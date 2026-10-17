class Handler {
    Object submit(Object ctx, Object request) {
        return this.assessments.run(ctx, request);
    }
}
