"""Match literal quotes while tolerating presentation-only differences.

No fuzzy matching, word deletion or paraphrase is used. Always return an actual
slice of the source, retaining the raw model answer separately for inspection.
"""
import unicodedata

PUNCTUATION={'。':'.','「':'"','」':'"','『':"'",'』':"'",'“':'"','”':'"','‘':"'",'’':"'"}

def normalized(text):
    chars=[];positions=[]
    for index,char in enumerate(text):
        for value in unicodedata.normalize('NFKC',char):
            if not value.isspace():
                chars.append(PUNCTUATION.get(value,value));positions.append(index)
    return ''.join(chars),positions

def match_quote(source,evidence):
    if not isinstance(evidence,str) or not evidence.strip():return None
    if evidence in source:return evidence
    source_key,positions=normalized(source)
    evidence_key,_=normalized(evidence)
    # Models may wrap an otherwise literal quote in quotation marks.
    evidence_key=evidence_key.strip('"\'')
    if not source_key or not evidence_key:return None
    index=source_key.find(evidence_key)
    if index>=0:
        return source[positions[index]:positions[index+len(evidence_key)-1]+1]
    # A duplicated quote may contain the entire source after a spurious prefix.
    # Only accept a complete source, optionally without its final punctuation.
    source_body=source_key.rstrip('.!?;"\'')
    if len(source_body)>=8 and source_body in evidence_key:
        return source
    return None
