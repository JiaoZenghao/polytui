use clap::Parser;
use polytui::{
    app::{INTERNAL_DIAGNOSTIC, NON_TTY_DIAGNOSTIC, Outcome, SystemRuntime, run_with},
    cli::Cli,
};
use std::process::ExitCode;

fn main() -> ExitCode {
    Cli::parse();

    let mut runtime = SystemRuntime;
    match run_with(&mut runtime) {
        Outcome::Success => ExitCode::SUCCESS,
        Outcome::NonTty => {
            eprintln!("{NON_TTY_DIAGNOSTIC}");
            ExitCode::from(2)
        }
        Outcome::InternalFailure => {
            eprintln!("{INTERNAL_DIAGNOSTIC}");
            ExitCode::from(1)
        }
    }
}
