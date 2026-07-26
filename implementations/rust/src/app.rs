use std::io::IsTerminal;

pub const NON_TTY_DIAGNOSTIC: &str = "polytui: interactive mode requires a TTY";
pub const INTERNAL_DIAGNOSTIC: &str = "polytui: interactive mode failed";

pub trait Runtime {
    fn stdin_is_terminal(&self) -> bool;
    fn stdout_is_terminal(&self) -> bool;
    fn run_tui(&mut self) -> std::io::Result<()>;
}

#[derive(Debug, Eq, PartialEq)]
pub enum Outcome {
    Success,
    NonTty,
    InternalFailure,
}

pub fn run_with(runtime: &mut dyn Runtime) -> Outcome {
    if !runtime.stdin_is_terminal() || !runtime.stdout_is_terminal() {
        return Outcome::NonTty;
    }
    match runtime.run_tui() {
        Ok(()) => Outcome::Success,
        Err(_) => Outcome::InternalFailure,
    }
}

pub struct SystemRuntime;

impl Runtime for SystemRuntime {
    fn stdin_is_terminal(&self) -> bool {
        std::io::stdin().is_terminal()
    }

    fn stdout_is_terminal(&self) -> bool {
        std::io::stdout().is_terminal()
    }

    fn run_tui(&mut self) -> std::io::Result<()> {
        crate::tui::run()
    }
}

#[cfg(test)]
mod tests {
    use std::io;

    use super::*;

    struct FakeRuntime {
        stdin_is_terminal: bool,
        stdout_is_terminal: bool,
        run_result: io::Result<()>,
        run_calls: usize,
    }

    impl Runtime for FakeRuntime {
        fn stdin_is_terminal(&self) -> bool {
            self.stdin_is_terminal
        }

        fn stdout_is_terminal(&self) -> bool {
            self.stdout_is_terminal
        }

        fn run_tui(&mut self) -> io::Result<()> {
            self.run_calls += 1;
            match &self.run_result {
                Ok(()) => Ok(()),
                Err(error) => Err(io::Error::new(error.kind(), error.to_string())),
            }
        }
    }

    #[test]
    fn non_tty_stdin_does_not_start_the_tui() {
        let mut runtime = FakeRuntime {
            stdin_is_terminal: false,
            stdout_is_terminal: true,
            run_result: Ok(()),
            run_calls: 0,
        };

        assert_eq!(run_with(&mut runtime), Outcome::NonTty);
        assert_eq!(runtime.run_calls, 0);
    }

    #[test]
    fn non_tty_stdout_does_not_start_the_tui() {
        let mut runtime = FakeRuntime {
            stdin_is_terminal: true,
            stdout_is_terminal: false,
            run_result: Ok(()),
            run_calls: 0,
        };

        assert_eq!(run_with(&mut runtime), Outcome::NonTty);
        assert_eq!(runtime.run_calls, 0);
    }

    #[test]
    fn terminal_streams_start_the_tui_once_and_succeed() {
        let mut runtime = FakeRuntime {
            stdin_is_terminal: true,
            stdout_is_terminal: true,
            run_result: Ok(()),
            run_calls: 0,
        };

        assert_eq!(run_with(&mut runtime), Outcome::Success);
        assert_eq!(runtime.run_calls, 1);
    }

    #[test]
    fn tui_io_error_maps_to_internal_failure() {
        let mut runtime = FakeRuntime {
            stdin_is_terminal: true,
            stdout_is_terminal: true,
            run_result: Err(io::Error::other("draw failed")),
            run_calls: 0,
        };

        assert_eq!(run_with(&mut runtime), Outcome::InternalFailure);
        assert_eq!(runtime.run_calls, 1);
    }
}
