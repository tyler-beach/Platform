class Request:
    def __init__(self, request_id: str):
        self.request_id = request_id

class Response:
    def __init__(self, accepted: bool):
        self.accepted = accepted

class Provider:
    def assess(self, request: Request) -> Response:
        return Response(True)

class Worker:
    def __init__(self):
        self.client = Provider()

    def execute(self, request: Request) -> Response:
        return self.client.assess(request)

class Handler:
    def __init__(self):
        self.provider = Provider()
        self.worker = Worker()

    def Submit(self, request: Request, enqueue: bool) -> Response:
        if enqueue:
            return self.worker.execute(request)
        return self.provider.assess(request)
