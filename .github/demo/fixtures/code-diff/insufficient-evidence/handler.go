package orders

func (h *Handler) Submit(ctx Context, request Request) error {
    _, err := h.assessments.Run(ctx, request)
    return err
}
