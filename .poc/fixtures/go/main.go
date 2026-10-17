package main

import "context"

type Request struct { ID string }
type Response struct { Accepted bool }

type Provider interface {
    Assess(context.Context, Request) (Response, error)
}

type AnthropicClient struct {}
func (c *AnthropicClient) Assess(ctx context.Context, req Request) (Response, error) {
    return Response{Accepted: true}, nil
}

type Worker struct { Client *AnthropicClient }
func (w *Worker) Execute(ctx context.Context, req Request) (Response, error) {
    // A transitive helper: the provider call is one level deeper than Submit.
    return w.Client.Assess(ctx, req)
}

type Handler struct {
    Provider Provider
    Worker *Worker
}

// Submit is the sample entry point for the end-to-end functional analysis PoC.
func (h *Handler) Submit(ctx context.Context, req Request, enqueue bool) (Response, error) {
    if enqueue {
        return h.Worker.Execute(ctx, req)
    }
    return h.Provider.Assess(ctx, req)
}
