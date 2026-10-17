class Handler {
  submit(ctx, request) {
    return this.assessments.run(ctx, request);
  }
}
