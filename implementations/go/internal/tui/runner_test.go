package tui

import (
	"errors"
	"os"
	"testing"

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

func testFiles(t *testing.T) (*os.File, *os.File) {
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
	return stdin, stdout
}
