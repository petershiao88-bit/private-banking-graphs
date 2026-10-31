function nativeAnswers(body,expected){
 if(body.error || body.errors?.length || !body.answers || typeof body.answers!=='object' || Array.isArray(body.answers))throw new Error('Jev 未回傳有效原生 answers。');
 if(typeof body.model!=='string' || !/^typesafe\/jev-1\.13(?:-|$)/.test(body.model))throw new Error('Jev 回傳模型不符合指定版本。');
 if(Object.keys(body.answers).length!==expected.length || expected.some(k=>!Object.hasOwn(body.answers,k)))throw new Error('Jev 原生評估漏項或有額外項目。');
 return (key,labels)=>{
  const a=body.answers[key],p=a?.probabilities;
  if(a?.type!=='choice' || !labels.includes(a.choice) || !p || Object.keys(p).length!==labels.length ||
   labels.some(k=>!Object.hasOwn(p,k)||typeof p[k]!=='number'||!Number.isFinite(p[k])||p[k]<0||p[k]>1) ||
   Math.abs(labels.reduce((s,k)=>s+p[k],0)-1)>0.02 || p[a.choice]<Math.max(...Object.values(p)))throw new Error('Jev 原生機率分布無效。');
  if(a.confidence!==undefined && (typeof a.confidence!=='number'||!Number.isFinite(a.confidence)||a.confidence<0||a.confidence>1))throw new Error('Jev confidence 無效。');
  return a;
 };
}
function decisionEvidence(body,scope,phase){return {requestId:body.id ?? null,model:body.model,provider:body.provider ?? null,scope,answers:body.answers,usage:body.usage ?? null,
 policy:{method:'native_choice',phase,numericThreshold:null,calibrated:false},probabilityMeaning:'Native P(included) independently per candidate; never normalized across candidates or multiplied across phases.'};}
