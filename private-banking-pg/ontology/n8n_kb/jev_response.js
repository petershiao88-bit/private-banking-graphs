function decisionEvidence(body,phase){
 return {requestId:body.id,model:body.model,provider:body.provider,answers:body.answers,usage:body.usage,phase};
}
