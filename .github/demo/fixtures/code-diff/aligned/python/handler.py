class Handler:
    def submit(self, ctx, request):
        job = self.jobs.enqueue(ctx, request)
        return job.id
