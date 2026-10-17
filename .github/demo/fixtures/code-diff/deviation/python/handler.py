class Handler:
    def submit(self, ctx, request):
        return self.anthropic.assess(ctx, request)
