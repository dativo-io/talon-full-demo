function selectLatestRequesterComment(comments, requesterId) {
  const id = String(requesterId ?? '');
  if (!id) return null;
  return (comments || []).find((comment) => comment && comment.public === true && String(comment.author_id) === id && typeof comment.plain_body === 'string' && comment.plain_body.trim() !== '') || null;
}
// Map the adapter's safe machine error contract ({code, retryable}) to an
// operator-facing action, without exposing provider or policy internals. The
// operator learns whether to retry, escalate, or contact the integration owner.
function operatorMessageForError(code, retryable) {
  switch (code) {
    case 'policy_denied':
      return 'Talon policy denied this draft. Keep the ticket with a human agent — retrying will not help.';
    case 'rate_limited':
      return 'Talon is rate limiting requests. Wait a moment and try again.';
    case 'integration_misconfigured':
      return 'The draft integration is misconfigured. Contact the integration owner; retrying will not help.';
    case 'service_unavailable':
      return 'The draft service is temporarily unavailable. You can retry shortly.';
    default:
      return retryable
        ? 'Draft unavailable right now. You can retry; otherwise keep this ticket with a human agent.'
        : 'Draft unavailable. Keep this ticket with a human agent.';
  }
}
function errorBodyFrom(error) {
  if (!error || typeof error !== 'object') return null;
  if (error.responseJSON && typeof error.responseJSON === 'object') return error.responseJSON;
  if (typeof error.responseText === 'string') {
    try { return JSON.parse(error.responseText); } catch (_) { return null; }
  }
  return null;
}
function validAdapterHostname(value) {
  if (typeof value !== 'string' || value.length > 253) return false;
  if (value === 'localhost' || /^[0-9.]+$/.test(value)) return false;
  const labels = value.split('.');
  return labels.length >= 2 && labels.every((label) => /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/i.test(label));
}
function initTalonZendeskApp() {
  const client = ZAFClient.init();
  const button = document.querySelector('#draft');
  const status = document.querySelector('#status');
  function setStatus(message, isError = false) { status.textContent = message; status.classList.toggle('error', isError); }
  async function run() {
    button.disabled = true; setStatus('Generating through Talon…');
    try {
      const values = await client.get(['ticket.id','ticket.subject','ticket.requester.id','ticket.requester.name','ticket.requester.email']);
      if (values.errors) throw new Error('Zendesk could not read ticket fields');
      const ticketId = String(values['ticket.id']);
      const requesterId = values['ticket.requester.id'];
      const commentsResponse = await client.request({url:`/api/v2/tickets/${encodeURIComponent(ticketId)}/comments.json?sort_order=desc&per_page=25`,type:'GET',accepts:'application/json',dataType:'json'});
      const latest = selectLatestRequesterComment(commentsResponse.comments, requesterId);
      if (!latest) throw new Error('No recent public requester comment found');
      const metadata = await client.metadata();
      const domain = String(metadata.settings.adapter_domain || '').trim();
      if (!validAdapterHostname(domain)) throw new Error('Invalid adapter domain');
      const response = await client.request({url:`https://${domain}/v1/zendesk/draft`,type:'POST',contentType:'application/json',accepts:'application/json',dataType:'json',headers:{Authorization:'Bearer {{setting.adapter_token}}','Content-Type':'application/json'},data:JSON.stringify({ticket_id:ticketId,subject:values['ticket.subject']||'',requester:{name:values['ticket.requester.name']||'Demo Customer',email:values['ticket.requester.email']||''},message:latest.plain_body}),secure:true});
      if (!response || typeof response.draft !== 'string' || response.draft.trim() === '') throw new Error('Adapter did not return a draft');
      await client.invoke('ticket.editor.insert', response.draft); setStatus(`Draft inserted · ${response.session_id}`);
    } catch (error) {
      console.error(error);
      const body = errorBodyFrom(error);
      setStatus(operatorMessageForError(body && body.code, !!(body && body.retryable)), true);
    }
    finally { button.disabled = false; }
  }
  button.addEventListener('click', run);
}
if (typeof module !== 'undefined' && module.exports) module.exports = {selectLatestRequesterComment, validAdapterHostname, operatorMessageForError, errorBodyFrom};
if (typeof window !== 'undefined' && window.ZAFClient) initTalonZendeskApp();
