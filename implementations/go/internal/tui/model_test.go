package tui

import (
	"strings"
	"testing"

	tea "charm.land/bubbletea/v2"
)

func TestModelView(t *testing.T) {
	got := strings.TrimSuffix(newModel().View().Content, "\n")
	want := "PolyTUI · Go\nPress Ctrl+C or Ctrl+D to exit"
	if got != want {
		t.Fatalf("View() = %q, want %q", got, want)
	}
}

func TestModelExitKeys(t *testing.T) {
	for _, key := range []rune{'c', 'd'} {
		_, command := newModel().Update(tea.KeyPressMsg(tea.Key{
			Code: key,
			Mod:  tea.ModCtrl,
		}))
		if command == nil {
			t.Fatalf("ctrl+%c did not request exit", key)
		}
		if _, ok := command().(tea.QuitMsg); !ok {
			t.Fatalf("ctrl+%c command did not return QuitMsg", key)
		}
	}
}

func TestModelIgnoresOtherKeys(t *testing.T) {
	_, command := newModel().Update(tea.KeyPressMsg(tea.Key{Code: 'x'}))
	if command != nil {
		t.Fatal("ordinary key requested an effect")
	}
}
