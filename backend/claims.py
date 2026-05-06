import spacy
nlp = spacy.load("en_core_web_sm")

def extract_candidate_claims(text: str, min_len:int=30, max_claims:int=50):
    """
    Heuristic: select sentences likely to contain factual, verifiable claims.
    This version prioritizes sentences with a clear subject-verb-object structure
    and named entities.
    """
    doc = nlp(text)
    claims = []
    
    for sent in doc.sents:
        s = sent.text.strip()
        if len(s) < min_len:
            continue
            
        sent_doc = nlp(s)
        
        # Check for presence of named entities (your original logic)
        has_entities = any(ent.label_ in ('PERSON', 'ORG', 'GPE', 'DATE', 'CARDINAL', 'PERCENT', 'MONEY') for ent in sent_doc.ents)
        
        # --- New Logic: Check for a root verb (indicates a core assertion) ---
        has_root_verb = any(token.dep_ == 'ROOT' and token.pos_ == 'VERB' for token in sent_doc)
        
        # A good claim often has both entities and a strong verb
        if has_entities and has_root_verb:
            claims.append(s)
        
        if len(claims) >= max_claims:
            break
            
    return claims if claims else [sent.text.strip() for sent in doc.sents][:max_claims]