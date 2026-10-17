interface Provider {
    Response assess(Request request);
}
final class Request {
    final String id;
    Request(String id) { this.id = id; }
}
final class Response {
    final boolean accepted;
    Response(boolean accepted) { this.accepted = accepted; }
}
class AnthropicProvider implements Provider {
    public Response assess(Request request) { return new Response(true); }
}
class Worker {
    private final AnthropicProvider provider;
    Worker(AnthropicProvider provider) { this.provider = provider; }
    Response execute(Request request) { return provider.assess(request); }
}
class Handler {
    private final Provider provider;
    private final Worker worker;
    Handler(Provider provider, Worker worker) { this.provider = provider; this.worker = worker; }
    Response Submit(Request request, boolean enqueue) {
        if (enqueue) return worker.execute(request);
        return provider.assess(request);
    }
}
