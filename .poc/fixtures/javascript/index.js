/**
 * @typedef {{id: string}} Request
 * @typedef {{accepted: boolean}} Response
 */
class AnthropicProvider {
  /** @param {Request} request @returns {Response} */
  assess(request) { return { accepted: true }; }
}
class Worker {
  /** @param {AnthropicProvider} provider */
  constructor(provider) { this.provider = provider; }
  /** @param {Request} request @returns {Response} */
  execute(request) { return this.provider.assess(request); }
}
class Handler {
  /** @param {AnthropicProvider} provider @param {Worker} worker */
  constructor(provider, worker) { this.provider = provider; this.worker = worker; }
  /** @param {Request} request @param {boolean} enqueue @returns {Response} */
  Submit(request, enqueue) {
    if (enqueue) return this.worker.execute(request);
    return this.provider.assess(request);
  }
}
module.exports = { Handler, Worker, AnthropicProvider };
