use std::io;

use crossterm::event::{self, Event, KeyCode, KeyEvent, KeyEventKind, KeyModifiers};
use ratatui::{Frame, TerminalOptions, Viewport, widgets::Paragraph};

pub const BANNER: &str = "PolyTUI · Rust";
pub const EXIT_HINT: &str = "Press Ctrl+C or Ctrl+D to exit";

pub fn run() -> io::Result<()> {
    let options = TerminalOptions {
        viewport: Viewport::Inline(2),
    };
    let mut terminal = match ratatui::try_init_with_options(options) {
        Ok(terminal) => terminal,
        Err(error) => {
            let _ = ratatui::try_restore();
            return Err(error);
        }
    };

    let operation = (|| -> io::Result<()> {
        terminal.draw(render)?;
        loop {
            if let Event::Key(key) = event::read()?
                && key.kind == KeyEventKind::Press
                && is_exit_key(key)
            {
                return Ok(());
            }
        }
    })();
    let restore = ratatui::try_restore();

    match operation {
        Err(error) => Err(error),
        Ok(()) => restore,
    }
}

pub fn is_exit_key(key: KeyEvent) -> bool {
    key.modifiers == KeyModifiers::CONTROL
        && matches!(key.code, KeyCode::Char('c') | KeyCode::Char('d'))
}

pub fn render(frame: &mut Frame) {
    frame.render_widget(
        Paragraph::new(format!("{BANNER}\n{EXIT_HINT}")),
        frame.area(),
    );
}

#[cfg(test)]
mod tests {
    use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};
    use ratatui::{Terminal, backend::TestBackend};

    use super::*;

    #[test]
    fn render_draws_the_banner_and_exit_hint_on_two_lines() {
        let mut terminal = Terminal::new(TestBackend::new(40, 2)).unwrap();

        let frame = terminal.draw(render).unwrap();
        let banner: String = (0..frame.area.width)
            .map(|x| frame.buffer[(x, 0)].symbol())
            .collect();
        let exit_hint: String = (0..frame.area.width)
            .map(|x| frame.buffer[(x, 1)].symbol())
            .collect();

        assert_eq!(banner.trim_end(), BANNER);
        assert_eq!(exit_hint.trim_end(), EXIT_HINT);
    }

    #[test]
    fn ctrl_c_and_ctrl_d_are_exit_keys_but_plain_x_is_not() {
        assert!(is_exit_key(KeyEvent::new(
            KeyCode::Char('c'),
            KeyModifiers::CONTROL,
        )));
        assert!(is_exit_key(KeyEvent::new(
            KeyCode::Char('d'),
            KeyModifiers::CONTROL,
        )));
        assert!(!is_exit_key(KeyEvent::new(
            KeyCode::Char('x'),
            KeyModifiers::NONE,
        )));
    }
}
