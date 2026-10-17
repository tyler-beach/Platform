package orders

func (h *Handler) Submit(ctx Context, request Request) (string, error) {
    job, err := h.jobs.Enqueue(ctx, request)
    if err != nil {
        return "", err
    }
    return job.ID, nil
}
