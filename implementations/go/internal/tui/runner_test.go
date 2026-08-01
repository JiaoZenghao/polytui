package tui

import (
	"errors"
	"io"
	"os"
	"strings"
	"testing"
	"time"

	tea "charm.land/bubbletea/v2"
)

func TestRunnerRejectsNonTerminalWithoutStartingProgram(t *testing.T) {
	stdin, stdout := testFiles(t)

	for _, test := range []struct {
		name       string
		isTerminal func(int) bool
	}{
		{
			name: "stdin",
			isTerminal: func(fd int) bool {
				return fd != int(stdin.Fd())
			},
		},
		{
			name: "stdout",
			isTerminal: func(fd int) bool {
				return fd != int(stdout.Fd())
			},
		},
	} {
		t.Run(test.name, func(t *testing.T) {
			calls := 0
			runner := Runner{
				stdin:      stdin,
				stdout:     stdout,
				isTerminal: test.isTerminal,
				runProgram: func(tea.Model, ...tea.ProgramOption) (tea.Model, error) {
					calls++
					return newModel(), nil
				},
			}

			if err := runner.Run(); !errors.Is(err, ErrNotTTY) {
				t.Fatalf("Run() error = %v, want ErrNotTTY", err)
			}
			if calls != 0 {
				t.Fatalf("runProgram calls = %d, want 0", calls)
			}
		})
	}
}

func TestRunnerStartsProgramForTerminals(t *testing.T) {
	stdin, stdout := testFiles(t)
	calls := 0
	runner := Runner{
		stdin:      stdin,
		stdout:     stdout,
		isTerminal: func(int) bool { return true },
		runProgram: func(tea.Model, ...tea.ProgramOption) (tea.Model, error) {
			calls++
			return newModel(), nil
		},
	}

	if err := runner.Run(); err != nil {
		t.Fatalf("Run() error = %v", err)
	}
	if calls != 1 {
		t.Fatalf("runProgram calls = %d, want 1", calls)
	}
}

func TestRunnerReturnsProgramError(t *testing.T) {
	stdin, stdout := testFiles(t)
	want := errors.New("program failed")
	runner := Runner{
		stdin:      stdin,
		stdout:     stdout,
		isTerminal: func(int) bool { return true },
		runProgram: func(tea.Model, ...tea.ProgramOption) (tea.Model, error) {
			return newModel(), want
		},
	}

	if err := runner.Run(); !errors.Is(err, want) {
		t.Fatalf("Run() error = %v, want %v", err, want)
	}
}

func TestRunnerPassesModelAndTerminalOptions(t *testing.T) {
	stdin, stdinWriter, stdoutReader, stdout := testStreams(t)
	runner := Runner{
		stdin:      stdin,
		stdout:     stdout,
		isTerminal: func(int) bool { return true },
		runSpec: func(spec programSpec) (tea.Model, error) {
			if spec.model == nil {
				t.Fatal("program model is nil")
			}
			const wantView = "PolyTUI · Go\nPress Ctrl+C or Ctrl+D to exit"
			if gotView := strings.TrimSuffix(spec.model.View().Content, "\n"); gotView != wantView {
				t.Fatalf("program model view = %q, want %q", gotView, wantView)
			}
			if gotOptions := len(spec.options); gotOptions != 2 {
				t.Fatalf("program options = %d, want 2", gotOptions)
			}

			program := tea.NewProgram(spec.model, spec.options...)
			results := make(chan error, 1)
			go func() {
				_, err := program.Run()
				results <- err
			}()
			if _, err := stdinWriter.Write([]byte{3}); err != nil {
				t.Fatalf("write Ctrl+C: %v", err)
			}
			select {
			case err := <-results:
				if err != nil {
					t.Fatalf("program run error = %v", err)
				}
			case <-time.After(time.Second):
				program.Kill()
				<-results
				t.Fatal("program did not receive Ctrl+C through configured input")
			}

			return spec.model, nil
		},
	}

	if err := runner.Run(); err != nil {
		t.Fatalf("Run() error = %v", err)
	}
	if err := stdout.Close(); err != nil {
		t.Fatalf("close output: %v", err)
	}
	output, err := io.ReadAll(stdoutReader)
	if err != nil {
		t.Fatalf("read output: %v", err)
	}
	if len(output) == 0 {
		t.Fatal("configured output did not receive program output")
	}
}

func testFiles(t *testing.T) (*os.File, *os.File) {
	stdin, _, _, stdout := testStreams(t)
	return stdin, stdout
}

func testStreams(t *testing.T) (*os.File, *os.File, *os.File, *os.File) {
	t.Helper()
	stdin, stdinWriter, err := os.Pipe()
	if err != nil {
		t.Fatal(err)
	}
	stdoutReader, stdout, err := os.Pipe()
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() {
		stdin.Close()
		stdinWriter.Close()
		stdoutReader.Close()
		stdout.Close()
	})
	return stdin, stdinWriter, stdoutReader, stdout
}
