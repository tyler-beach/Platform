class Handler {
  submit(ctx, request) {
    return this.anthropic.assess(ctx, request);
  }
}
