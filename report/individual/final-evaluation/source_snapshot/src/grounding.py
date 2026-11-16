"""Bounded deterministic grounding proofs. No similarity score, gold or model.

Accepted rewrites are intentionally few. Unknown paraphrases fail closed.
"""
import re
import unicodedata
from decimal import Decimal

UNITS={
 'hour':'hour','hours':'hour','hr':'hour','hrs':'hour',
 'minute':'minute','minutes':'minute','min':'minute','mins':'minute',
 'second':'second','seconds':'second','sec':'second','secs':'second',
 'millimetre':'mm','millimetres':'mm','millimeter':'mm','millimeters':'mm','mm':'mm',
 'metre':'m','metres':'m','meter':'m','meters':'m','m':'m',
 'kilogram':'kg','kilograms':'kg','kg':'kg','grams':'g','gram':'g','g':'g',
 'volts':'v','volt':'v','v':'v','amperes':'a','ampere':'a','amps':'a','amp':'a','a':'a',
 'pascal':'pa','pascals':'pa','pa':'pa','kpa':'kpa','mpa':'mpa','bar':'bar',
 'megapascal':'mpa','millipascal':'millipascal',
 'milliamperes':'milliampere','millivolts':'millivolt','milliwatts':'milliwatt',
 'milliseconds':'millisecond','megawatts':'megawatt',
 'watt':'w','watts':'w','w':'w','kw':'kw','hz':'hz','khz':'khz',
}
CONDITIONS={'if','when','unless','while','only','provided','before','after','until','during','except','otherwise'}
MODALS={'can','may','must','should','shall','will','might','could','would'}
QUALIFIERS={'maximum','minimum','max','least','most','less','more','than','exactly','about','approximately','plusminus',
            'recommended','optional','required','always','normally','usually','all','any','some','each','every','either','both'}
NEGATIONS={'not','never','no','without','neither','nor'}


def normalize(text):
    text=unicodedata.normalize('NFC',text)
    # SI prefix case changes magnitudes: preserve it before English casefold.
    symbols={'mA':'milliampere','MA':'megaampere','mV':'millivolt','MV':'megavolt',
             'mW':'milliwatt','MW':'megawatt','mPa':'millipascal','MPa':'megapascal',
             'Mm':'megametre','ms':'millisecond','Ms':'megasecond','S':'siemens'}
    text=re.sub(r'(?<![A-Za-z])(?:'+ '|'.join(map(re.escape,symbols)) +r')(?![A-Za-z])',lambda m:symbols[m.group()],text)
    text=text.casefold()
    text=text.translate(str.maketrans({'\u2212':'-','\u2010':'-','\u2011':'-','\u2013':'-','\u2014':'-','\u2264':'<=','\u2265':'>=','\u2260':'!=','\u00b1':' plusminus ','\u2248':' approximately ', '\u2018':"'",'\u2019':"'",'\u201c':'"','\u201d':'"'}))
    # These are spelling/contraction equivalences, not changes in modal strength.
    text=re.sub(r'\bcannot\b','can not',text)
    for word,expanded in {"can't":'can not',"mustn't":'must not',"shouldn't":'should not',"isn't":'is not',"aren't":'are not',"doesn't":'does not',"don't":'do not'}.items():
        text=re.sub(r'\b'+re.escape(word)+r'\b',expanded,text)
    return ' '.join(text.split())


def tokens(text):
    parts=re.findall(r'[+-]?\d+(?:\.\d+)?|[^\W\d_]+|[<>]=?|[%°²³]|[+/\-=]',normalize(text),re.UNICODE)
    output=[]
    for part in parts:
        if re.fullmatch(r'[+-]?\d+(?:\.\d+)?',part):part=str(Decimal(part).normalize())
        output.append(UNITS.get(part,part))
    return tuple(output)


def sentences(evidence):
    # Split sentence-ending punctuation; decimal points are preserved. Table
    # geometry/headers are not inferred; ambiguous extraction may fail closed.
    text=' '.join(unicodedata.normalize('NFC',evidence).split())
    return [x.strip() for x in re.split(r'(?<=[.!?;])\s+(?!\d)',text) if x.strip()]


def protected(seq):
    numbers=tuple(x for x in seq if re.fullmatch(r'[+-]?\d+(?:\.\d+)?(?:E[+-]?\d+)?',x))
    quantities=tuple((x,seq[i+1] if i+1<len(seq) and seq[i+1] in set(UNITS.values())|{'%','°'} else None)
                     for i,x in enumerate(seq) if re.fullmatch(r'[+-]?\d+(?:\.\d+)?(?:E[+-]?\d+)?',x))
    return {'numbers':numbers,'quantities':quantities,'units':tuple(x for x in seq if x in set(UNITS.values())-{'a'}),
            'negation':tuple(x for x in seq if x in NEGATIONS),
            'conditions':tuple(x for x in seq if x in CONDITIONS),
            'modality':tuple(x for x in seq if x in MODALS),
            'qualifiers':tuple(x for x in seq if x in QUALIFIERS),
            'operators':tuple(x for x in seq if x in {'<','>','<=','>=','!=','='})}


def verify_grounding(claim,evidence):
    """Return a proof method or specific failure; never accept by token overlap.

    Source sentence windows preserve subjects, order, conditions, modality,
    numbers and units. The sole syntax rewrite joins adjacent affirmative
    sentences with 'and'. It is disallowed for guarded/negative/modal clauses.
    """
    target=tokens(claim)
    if not target:return {'passed':False,'reason':'empty_claim','method':None}
    source=sentences(evidence)
    seen=[]
    for start in range(len(source)):
        for size in range(1,min(3,len(source)-start)+1):
            window=source[start:start+size]
            if any('?' in sentence for sentence in window):continue
            seq=tokens(' '.join(window))
            guards=protected(seq);claim_guards=protected(target)
            seen.append(guards)
            # Equal complete token sequences: punctuation, case, unit aliases and
            # contraction normalization only. No word deletion/reordering.
            if target==seq:
                return {'passed':True,'reason':None,'method':'canonical_sentence_equivalence','source_sentence_range':[start,start+size]}
            if size>1 and not any(guards[k] for k in ('negation','conditions','modality','qualifiers')):
                joined=tokens(' and '.join(window))
                if target==joined:
                    return {'passed':True,'reason':None,'method':'adjacent_affirmative_sentence_conjunction','source_sentence_range':[start,start+size]}
            # Exact excerpt allowed only if it drops no protected fact from its
            # containing sentence. This blocks stripping 'not', 'if' or values.
            if size==1 and len(target)<=len(seq) and guards==claim_guards:
                if any(seq[i:i+len(target)]==target for i in range(len(seq)-len(target)+1)):
                    return {'passed':True,'reason':None,'method':'guard_preserving_exact_excerpt','source_sentence_range':[start,start+1]}
    if not seen:return {'passed':False,'reason':'no_evidence_text','method':None}
    cg=protected(target)
    # Diagnostics only: mismatches never trigger a relaxed acceptance route.
    reason='unverified_paraphrase_or_added_information'
    for field,label in [('numbers','numeric_mismatch'),('quantities','numeric_or_unit_mismatch'),('units','unit_mismatch'),
                        ('negation','negation_mismatch'),('conditions','condition_mismatch'),('modality','modality_mismatch'),('operators','comparison_mismatch'),('qualifiers','qualifier_mismatch')]:
        if not any(g[field]==cg[field] for g in seen):reason=label;break
    return {'passed':False,'reason':reason,'method':None}
