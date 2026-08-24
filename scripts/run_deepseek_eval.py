"""Run a budget-capped DeepSeek evaluation. The key is read only from the environment."""
from __future__ import annotations
import argparse, json, os, statistics, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]; DATA = ROOT / "data"; LOCAL = ROOT / "work" / "eval-runs"

def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def percentile(values, q):
    if not values: return 0
    values=sorted(values); return values[min(len(values)-1, round((len(values)-1)*q))]
def cost_cny(usage, price, fx):
    hit=usage.get("prompt_cache_hit_tokens",0); prompt=usage.get("prompt_tokens",0); miss=usage.get("prompt_cache_miss_tokens", max(0,prompt-hit)); out=usage.get("completion_tokens",0)
    return ((hit*price["inputCacheHit"] + miss*price["inputCacheMiss"] + out*price["output"])/1_000_000)*fx
def estimate_call_cost(config, item):
    price=config["pricingSnapshot"][item["priceKey"]]; generation=config["generation"]
    return cost_cny({"prompt_tokens":generation.get("maxInputTokensEstimate",1600),"completion_tokens":generation["maxTokens"]},price,config["usdToCny"])
def estimate_run_cost(config, dataset):
    return sum(estimate_call_cost(config, item)*len(cases(dataset)) for item in config["configurations"])
def parse_json(text):
    try: return json.loads(text.strip())
    except (json.JSONDecodeError, TypeError): return None
def score(case, text):
    lower=(text or "").lower(); keys=case.get("keywords",[]); cites=case.get("citations",[])
    key_rate=sum(k.lower() in lower for k in keys)/max(1,len(keys)); cite_rate=sum(c.lower() in lower for c in cites)/max(1,len(cites)); obj=parse_json(text)
    schema=1 if not case.get("required_fields") else int(isinstance(obj,dict) and all(k in obj for k in case["required_fields"]))
    return {"quality":round(100*(.55*key_rate+.30*cite_rate+.15*schema),1),"citationHit":cite_rate,"jsonValid":int(obj is not None),"schemaValid":schema}
def prompt_for(case):
    context="\n".join(f"[{x['id']}] {x['text']}" for x in case["context"])
    return f"你是企业研究助手。只能依据参考材料回答，并在答案中写出引用编号。{case['prompt']}\n参考材料：\n{context}"
def mock_answer(case): return json.dumps({"answer":"；".join(case["keywords"]),"citations":case["citations"], **{k:"已提取" for k in case.get("required_fields",[])}},ensure_ascii=False)
def request_live(config, payload, key, timeout):
    req=Request(config["baseUrl"],data=json.dumps(payload).encode(),headers={"Content-Type":"application/json","Authorization":f"Bearer {key}"})
    with urlopen(req, timeout=timeout) as response: return json.loads(response.read().decode())
def cases(dataset): return [(s["id"],c) for s in dataset["scenarios"] for c in s["cases"]]
def run(live, config, dataset, budget):
    key=os.getenv("DEEPSEEK_API_KEY")
    if live and not key: raise RuntimeError("缺少 DEEPSEEK_API_KEY；不要把 Key 写入文件。")
    all_cases=cases(dataset); result=[]; local=[]; spent=0.0
    for item in config["configurations"]:
        rows=[]; price=config["pricingSnapshot"][item["priceKey"]]
        for scenario, case in all_cases:
            if spent + estimate_call_cost(config, item) > budget: break
            start=time.perf_counter()
            try:
                if live:
                    payload={"model":item["model"],"messages":[{"role":"system","content":"Return a concise answer. Do not reveal reasoning."},{"role":"user","content":prompt_for(case)}],"temperature":config["generation"]["temperature"],"max_tokens":config["generation"]["maxTokens"],"stream":False,"thinking":{"type":item["thinking"]}}
                    if item.get("reasoningEffort"): payload["reasoning_effort"]=item["reasoningEffort"]
                    response=request_live(config,payload,key,config["generation"]["timeoutSeconds"]); text=response["choices"][0]["message"].get("content",""); usage=response.get("usage",{}); charge=cost_cny(usage,price,config["usdToCny"])
                else: text=mock_answer(case); usage={"prompt_tokens":0,"completion_tokens":0}; charge=0
                latency=(time.perf_counter()-start)*1000; metrics=score(case,text); spent+=charge
                rows.append({"scenario":scenario,"caseId":case["id"],"latencyMs":round(latency,1),"costCny":charge,"usage":usage,**metrics}); local.append({"configuration":item["id"],"caseId":case["id"],"response":text,**metrics})
            except Exception as exc: rows.append({"scenario":scenario,"caseId":case["id"],"error":str(exc)[:200],"latencyMs":round((time.perf_counter()-start)*1000,1),"costCny":0})
        ok=[r for r in rows if "error" not in r]; result.append({"id":item["id"],"label":item["label"],"model":item["model"],"thinking":item["thinking"],"samples":len(rows),"quality":round(statistics.mean([r["quality"] for r in ok]),1) if ok else 0,"citationHitRate":round(100*statistics.mean([r["citationHit"] for r in ok]),1) if ok else 0,"jsonValidRate":round(100*statistics.mean([r["jsonValid"] for r in ok]),1) if ok else 0,"latencyMs":{"p50":round(percentile([r["latencyMs"] for r in ok],.5),1),"p95":round(percentile([r["latencyMs"] for r in ok],.95),1)},"costCny":round(sum(r["costCny"] for r in rows),4),"failureRate":round(100*(len(rows)-len(ok))/max(1,len(rows)),1)})
    return result, local, spent
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--live",action="store_true"); ap.add_argument("--budget-cny",type=float,default=20); ap.add_argument("--out",type=Path,default=DATA/"eval-results.json"); args=ap.parse_args()
    config=load(DATA/"eval-config.json"); dataset=load(DATA/"eval-scenarios.json"); total=len(cases(dataset))*len(config["configurations"]); budget=min(args.budget_cny,config["budgetCny"]); estimate=estimate_run_cost(config,dataset)
    print(f"{total} calls planned; budget ceiling: CNY {budget:.2f}. Worst-case estimate: CNY {estimate:.4f}. {'LIVE' if args.live else 'MOCK (no API calls)'}")
    if args.live and estimate > budget: raise RuntimeError("最坏情况费用预估超过预算；请降低题数、maxTokens 或提高已明确授权的预算。")
    rows, raw, spent=run(args.live,config,dataset,budget)
    status="real" if args.live else "mock"; output={"schemaVersion":"0.3.0","status":status,"runAt":datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),"provider":config["provider"],"datasetVersion":dataset["version"],"budgetCny":budget,"estimatedWorstCaseCny":round(estimate,4),"actualCostCny":round(spent,4),"pricingSnapshot":config["pricingSnapshot"],"configurations":rows,"humanReview":"pending"}
    args.out.parent.mkdir(parents=True, exist_ok=True); args.out.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    LOCAL.mkdir(parents=True,exist_ok=True); (LOCAL/"latest-responses.json").write_text(json.dumps(raw,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if args.live:
        review={"status":"pending","instruction":"每组抽取 5 条，人工填写 1-5 分；不要把模型思考过程写入复核表。","fields":["configuration","caseId","factuality_1_to_5","completeness_1_to_5","citation_correctness_1_to_5","reviewerNote"],"samples":[]}
        for item in config["configurations"]:
            review["samples"] += [{"configuration":item["id"],"caseId":row["caseId"],"factuality_1_to_5":None,"completeness_1_to_5":None,"citation_correctness_1_to_5":None,"reviewerNote":""} for row in raw if row["configuration"]==item["id"]][:5]
        (DATA/"eval-review-template.json").write_text(json.dumps(review,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Wrote {args.out}; actual cost: CNY {spent:.4f}")
if __name__=="__main__": main()
