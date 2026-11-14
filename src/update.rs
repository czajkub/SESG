use crossterm::event::KeyEventKind;
use ratatui::crossterm::event::{KeyCode, KeyEvent, KeyModifiers};

use crate::app::App;

pub fn update(app: &mut App, key_event: KeyEvent) {
    match key_event.code {
        KeyCode::Esc | KeyCode::Char('q') => app.quit(),
        KeyCode::Char('c') | KeyCode::Char('C') if key_event.modifiers == KeyModifiers::CONTROL => {
            app.quit()
        }
        KeyCode::Char('a') => app.scroll_aspect(),
        KeyCode::Char('t') => app.scroll_time(),
        KeyCode::Enter if key_event.kind == KeyEventKind::Press => app.generate_sentence(),
        _ => {}
    };
}