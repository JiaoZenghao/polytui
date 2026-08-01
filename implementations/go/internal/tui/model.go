package tui

import tea "charm.land/bubbletea/v2"

const (
	Banner   = "PolyTUI · Go"
	ExitHint = "Press Ctrl+C or Ctrl+D to exit"
)

type model struct{}

func newModel() model { return model{} }

func (model) Init() tea.Cmd { return nil }

func (m model) Update(message tea.Msg) (tea.Model, tea.Cmd) {
	if key, ok := message.(tea.KeyPressMsg); ok {
		switch key.Keystroke() {
		case "ctrl+c", "ctrl+d":
			return m, tea.Quit
		}
	}
	return m, nil
}

func (model) View() tea.View {
	return tea.NewView(Banner + "\n" + ExitHint + "\n")
}
