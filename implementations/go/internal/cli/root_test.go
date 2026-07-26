package cli

import (
	"bytes"
	"testing"
)

func TestVersionFlag(t *testing.T) {
	t.Parallel()

	var output bytes.Buffer
	command := NewRootCommand()
	command.SetOut(&output)
	command.SetErr(&output)
	command.SetArgs([]string{"--version"})

	if err := command.Execute(); err != nil {
		t.Fatalf("Execute() error = %v", err)
	}

	const want = "polytui 0.1.0-dev.0 (go)\n"
	if got := output.String(); got != want {
		t.Fatalf("version output = %q, want %q", got, want)
	}
}
