const graphRows=body=>body.data.values.map(row=>Object.fromEntries(body.data.fields.map((key,i)=>[key,row[i]])));
const canonical=value=>Array.isArray(value)?value.map(canonical):value&&typeof value==='object'?Object.fromEntries(Object.keys(value).sort().map(key=>[key,canonical(value[key])])):value;
const stableKey=(prefix,value)=>{const text=JSON.stringify(canonical(value));let a=2166136261,b=3339675911;for(let i=0;i<text.length;i++){a=Math.imul(a^text.charCodeAt(i),16777619);b=Math.imul(b^text.charCodeAt(i),2246822519);}return `${prefix}::${(a>>>0).toString(16).padStart(8,'0')}${(b>>>0).toString(16).padStart(8,'0')}`;};
const uniqueBy=(values,key)=>[...new Map(values.map(value=>[key(value),value])).values()];
const decisionEvidence=(body,phase)=>({requestId:body.id,model:body.model,provider:body.provider,answers:body.answers,usage:body.usage,phase,...(body.error?{error:body.error}:{})});
const scored=(candidate,answer)=>({...candidate,choice:answer.choice,judgement:answer.choice,probability:answer.probabilities.included,probabilities:answer.probabilities,confidence:answer.confidence});
