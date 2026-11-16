"""Exactly one minimal OpenAI request; no Agent, retrieval, benchmark or retries."""
import argparse
import json
import logging
import os
import re
from pathlib import Path
import time

ROOT=Path(__file__).resolve().parents[1]


# The Responses API reference specifies minimum 16. No live request is made
# merely by importing this module or preparing this corrected configuration.
MAX_OUTPUT_TOKENS=16


def filtered_error(exc, secrets=()):
    """Allowlist error metadata and render a safe validation message.

    Never log str(exc), raw body/message, request/response objects or headers.
    Free-form provider messages can echo prompt text, credentials or account data.
    Only known parameter names and numeric constraints survive message filtering.
    """
    codes={'invalid_value','invalid_request_error','invalid_type','invalid_parameter',
           'unsupported_value','unsupported_parameter','missing_required_parameter',
           'context_length_exceeded','model_not_found','rate_limit_exceeded',
           'insufficient_quota','invalid_api_key','permission_denied'}
    types={'invalid_request_error','authentication_error','permission_error',
           'rate_limit_error','server_error','api_error'}
    params={'model','input','messages','max_output_tokens','max_completion_tokens',
            'temperature','tools','tool_choice','store','parallel_tool_calls'}
    def clean(value, allowed):
        if value is None:return None
        if not isinstance(value,str) or any(secret and secret in value for secret in secrets):return '[filtered]'
        return value if value in allowed else '[filtered]'
    body=getattr(exc,'body',None)
    body=body if isinstance(body,dict) else {}
    if isinstance(body.get('error'),dict):body=body['error']
    result={'status_code':getattr(exc,'status_code',None),
            'error':{'code':clean(body.get('code',getattr(exc,'code',None)),codes),
                     'type':clean(body.get('type',getattr(exc,'type',None)),types),
                     'param':clean(body.get('param',getattr(exc,'param',None)),params)}}
    if result['status_code']==400:
        param=result['error']['param']
        message='Request rejected (HTTP 400).'
        if param and param!='[filtered]':message+=' Invalid or unsupported parameter: '+param+'.'
        raw=body.get('message')
        # A numeric minimum is safe and useful; quoted values, URLs and arbitrary
        # message text are not retained. This is not a copy of the server message.
        if param=='max_output_tokens' and isinstance(raw,str):
            minimum=re.search(r'(?:minimum(?: value)?(?: is| of)?|>=)\s*[:=]?\s*(\d{1,8})(?!\d)',raw,re.I)
            if minimum:message+=' Minimum allowed: '+minimum.group(1)+'.'
        result['error']['message']=message
        result['error']['message_policy']='Allowlisted summary; free-form provider text omitted'
    elif type(exc).__name__=='APITimeoutError':
        result['error']['message']='OpenAI request timed out; no automatic retry.'
    else:
        result['error']['message']='Request failed; free-form exception and provider text omitted.'
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'report/individual/openai-diagnostic-01.json')
    args=p.parse_args()
    if args.output.exists():raise SystemExit('Diagnostic output exists; refusing another request')
    from dotenv import load_dotenv
    load_dotenv(ROOT/'.env',override=False,encoding='utf-8-sig')
    key=os.getenv('OPENAI_API_KEY','').strip()
    if not key:raise SystemExit('OPENAI_API_KEY absent; no request attempted')
    for name in ('openai','httpx','httpx2','httpcore','httpcore2'):
        logging.getLogger(name).disabled=True
    from openai import OpenAI,DefaultHttpxClient
    import openai
    start=time.perf_counter()
    report={'status':'prepared','key_present':True,'sdk_version':openai.__version__,
            'endpoint':'https://api.openai.com/v1/responses','requested_model':'gpt-4.1-mini',
            'input':'Reply OK','max_output_tokens':MAX_OUTPUT_TOKENS,'timeout_seconds':20,'max_retries':0,
            'follow_redirects':False,'trust_env':True,'request_attempts':0,'network_events':[],
            'proxy_environment_present':{n:bool(os.getenv(n) or os.getenv(n.lower())) for n in ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','NO_PROXY')},
            'usage':None,'actual_model':None,'cost_usd':None}
    def trace(name,info):
        # Never store info dictionaries: they can contain request/header objects.
        item={'event':name,'elapsed_ms':round((time.perf_counter()-start)*1000,3)}
        if isinstance(info.get('exception'),BaseException):item['exception_type']=type(info['exception']).__name__
        report['network_events'].append(item)
    def request_hook(request):
        report['request_attempts']+=1
        if report['request_attempts']>1:raise RuntimeError('Single-request budget exceeded')
        if request.url.host!='api.openai.com' or request.url.path!='/v1/responses':raise RuntimeError('Unexpected diagnostic endpoint')
        request.extensions['trace']=trace
        report['payload_bytes']=len(request.content)
        # Keys and size only; headers are never enumerated or logged.
        report['payload_fields']=sorted(json.loads(request.content).keys())
    def response_hook(response):
        report['http_status']=response.status_code
    args.output.parent.mkdir(parents=True,exist_ok=True)
    # Persist a marker before connecting so rerunning the same command cannot
    # silently submit another request after a timeout/process interruption.
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    client=OpenAI(api_key=key,base_url='https://api.openai.com/v1',timeout=20.0,max_retries=0,
                  http_client=DefaultHttpxClient(timeout=20.0,follow_redirects=False,trust_env=True,
                      event_hooks={'request':[request_hook],'response':[response_hook]}))
    request_start=time.perf_counter()
    try:
        result=client.responses.create(model='gpt-4.1-mini',input='Reply OK',max_output_tokens=MAX_OUTPUT_TOKENS,store=False)
        report.update(status='success',response_status=result.status,actual_model=result.model,
                      reply_is_ok=result.output_text.strip()=='OK',
                      response_text=re.sub(r'sk-[A-Za-z0-9_-]+','[REDACTED]',result.output_text.replace(key,'[REDACTED]')),
                      usage=result.usage.model_dump() if result.usage else None,
                      request_id=getattr(result,'_request_id',None))
    except Exception as exc:
        causes=[];current=exc;seen=set()
        while current is not None and id(current) not in seen:
            seen.add(id(current));causes.append(type(current).__name__)
            current=current.__cause__ or current.__context__
        report.update(filtered_error(exc,secrets=(key,)))
        report.update(status='error',exception_types=causes,http_status=getattr(exc,'status_code',report.get('http_status')),
                      request_id=getattr(exc,'request_id',None))
    finally:
        report['latency_ms']=round((time.perf_counter()-request_start)*1000,3)
        client.close()
        args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    # Output only allowlisted, credential-free report fields.
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
