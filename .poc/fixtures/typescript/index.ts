export interface Request { id: string }
export interface Response { accepted: boolean }
export interface Provider { assess(request: Request): Response }

export class AnthropicProvider implements Provider {
  assess(request: Request): Response { return { accepted: true }; }
}
export class Worker {
  constructor(private provider: AnthropicProvider) {}
  execute(request: Request): Response { return this.provider.assess(request); }
}
export class Handler {
  constructor(private provider: Provider, private worker: Worker) {}
  Submit(request: Request, enqueue: boolean): Response {
    if (enqueue) return this.worker.execute(request);
    return this.provider.assess(request);
  }
}
