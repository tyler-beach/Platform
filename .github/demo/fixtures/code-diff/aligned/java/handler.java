class Handler {
    Object submit(Object ctx, Object request) {
        Object job = this.jobs.enqueue(ctx, request);
        return job;
    }
}
