# Zendesk private app

Runs in the Support ticket editor, selects the newest public requester comment, calls the private adapter through Zendesk's server-side request proxy, and inserts the returned draft. Configure `adapter_domain` as a hostname only and `adapter_token` as a secure header-scoped setting. The final test must use an uploaded private app because the local ZCLI server does not exercise secure settings.
