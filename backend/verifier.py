from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

MODEL_NAME = "cross-encoder/nli-roberta-base"

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
id2label = model.config.id2label

def nli_scores(premise: str, hypothesis: str):
    inputs = tokenizer.encode_plus(premise, hypothesis, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        logits = model(**inputs).logits
    probs = torch.softmax(logits, dim=1).cpu().numpy()[0]
    label_map = {id2label[i].lower(): float(probs[i]) for i in range(len(probs))}
    return label_map

def aggregate_verdict_from_evidence(claim: str, evidences: list, entail_thresh=0.7, contra_thresh=0.7):
    evidence_results = []
    max_entail = 0.0
    max_contra = 0.0
    for ev in evidences:
        premise = ev['content'][:2000]
        scores = nli_scores(premise, claim)
        entail = scores.get('entailment', 0.0)
        contra = scores.get('contradiction', 0.0)
        evidence_results.append({'title': ev.get('title'), 'url': ev.get('url'), 'scores': scores})
        max_entail = max(max_entail, entail)
        max_contra = max(max_contra, contra)

    if max_contra >= contra_thresh and max_contra > max_entail:
        verdict = 'refuted'
    elif max_entail >= entail_thresh and max_entail >= max_contra:
        verdict = 'supported'
    else:
        verdict = 'not_enough_info'
    return verdict, evidence_results
