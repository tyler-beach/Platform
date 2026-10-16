.PHONY: proto-format proto-lint proto-breaking proto-generate proto-check

proto-format:
	buf format -w proto

proto-lint:
	buf lint

proto-breaking:
	buf breaking --against '.git#branch=main'

proto-generate:
	buf generate

proto-check:
	buf lint
	buf build
