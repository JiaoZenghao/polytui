package cli

import (
	"bytes"
	"errors"
	"testing"

	"github.com/JiaoZenghao/polytui/implementations/go/internal/tui"
)

func TestVersionFlag(t *testing.T) {
	t.Parallel()

	var output bytes.Buffer
	command := NewRootCommand(func() error {
		t.Fatal("version flag ran interactive runner")
		return nil
	})
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

func TestDefaultActionRunsInteractiveOnce(t *testing.T) {
	calls := 0
	command := NewRootCommand(func() error {
		calls++
		return nil
	})
	command.SetArgs(nil)
	if err := command.Execute(); err != nil {
		t.Fatal(err)
	}
	if calls != 1 {
		t.Fatalf("calls = %d, want 1", calls)
	}
}

func TestVersionAndHelpBypassInteractive(t *testing.T) {
	for _, args := range [][]string{{"--version"}, {"--help"}} {
		calls := 0
		command := NewRootCommand(func() error {
			calls++
			return nil
		})
		command.SetArgs(args)
		command.SetOut(&bytes.Buffer{})
		if err := command.Execute(); err != nil {
			t.Fatal(err)
		}
		if calls != 0 {
			t.Fatalf("%v called interactive runner %d time(s)", args, calls)
		}
	}
}

func TestExecuteMapsInteractiveResult(t *testing.T) {
	tests := []struct {
		name     string
		run      func() error
		wantCode int
		wantErr  string
	}{
		{
			name:     "success",
			run:      func() error { return nil },
			wantCode: 0,
			wantErr:  "",
		},
		{
			name:     "non tty",
			run:      func() error { return tui.ErrNotTTY },
			wantCode: 2,
			wantErr:  "polytui: interactive mode requires a TTY\n",
		},
		{
			name:     "internal",
			run:      func() error { return errors.New("boom") },
			wantCode: 1,
			wantErr:  "polytui: interactive mode failed\n",
		},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			var stdout, stderr bytes.Buffer
			gotCode := Execute(nil, &stdout, &stderr, test.run)

			if gotCode != test.wantCode {
				t.Fatalf("Execute() = %d, want %d", gotCode, test.wantCode)
			}
			if gotErr := stderr.String(); gotErr != test.wantErr {
				t.Fatalf("stderr = %q, want %q", gotErr, test.wantErr)
			}
		})
	}
}
