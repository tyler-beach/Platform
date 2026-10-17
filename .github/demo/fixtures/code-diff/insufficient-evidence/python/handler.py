class Handler:
    def submit(self, ctx, request):
        return self.assessments.run(ctx, request)
