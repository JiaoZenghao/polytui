package tui

import (
	"errors"
	"os"

	tea "charm.land/bubbletea/v2"
	"golang.org/x/term"
)

var ErrNotTTY = errors.New("interactive mode requires a TTY")

type ProgramRunner func(tea.Model, ...tea.ProgramOption) (tea.Model, error)

type Runner struct {
	stdin      *os.File
	stdout     *os.File
	isTerminal func(int) bool
	runProgram ProgramRunner
}

func NewRunner(stdin, stdout *os.File) Runner {
	return Runner{
		stdin:      stdin,
		stdout:     stdout,
		isTerminal: term.IsTerminal,
		runProgram: func(model tea.Model, options ...tea.ProgramOption) (tea.Model, error) {
			return tea.NewProgram(model, options...).Run()
		},
	}
}

func (runner Runner) Run() error {
	if !runner.isTerminal(int(runner.stdin.Fd())) ||
		!runner.isTerminal(int(runner.stdout.Fd())) {
		return ErrNotTTY
	}
	_, err := runner.runProgram(
		newModel(),
		tea.WithInput(runner.stdin),
		tea.WithOutput(runner.stdout),
	)
	return err
}
