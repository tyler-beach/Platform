class Handler {
    Object submit(Object ctx, Object request) {
        return this.anthropic.assess(ctx, request);
    }
}
