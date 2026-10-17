package orders

func (h *Handler) Submit(ctx Context, request Request) error {
    _, err := h.anthropic.Assess(ctx, request)
    return err
}
