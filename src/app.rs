use color_eyre::Result;
use crate::words::{read_nouns, read_verbs, Noun, Verb};

#[derive(Debug)]
pub struct App {
    pub should_quit: bool,

    nouns: Vec<Noun>,
    verbs: Vec<Verb>,

    pub time: Time,
    pub aspect: Aspect,

    pub sentence: String,

    // TODO: sentence type
    // affirmative by default

    // TODO: subject options
    // default - "the" + singular noun, skip plural only

    // TODO: object
    // "the" + singular noun if transitive or ambi; none if intransitive

    // So: default sentence without completed todos for now is
    // the <subject> <verb_phrase> the <object>

    pub counter: u8,
}

#[derive(Clone, Copy, Debug, Default)]
pub enum Time {
    #[default]
    Present,
    Past,
    Future,
}

#[derive(Clone, Copy, Debug, Default)]
pub enum Aspect {
    #[default]
    Simple,
    Continuous,
    Perfect,
    PerfectContinuous,
}

impl App {
    pub fn new() -> Result<Self> {
        Ok(Self {
            should_quit: false,
            nouns: read_nouns()?,
            verbs: read_verbs()?,
            time: Time::default(),
            aspect: Aspect::default(),
            sentence: "The Example Is Sentenced".to_string(),
            counter: 0,
        })
    }

    pub fn tick(&self) {}

    pub fn quit(&mut self) {
        self.should_quit = true;
    }

    pub fn scroll_aspect(&mut self) {
        use Aspect::*;
        self.aspect = match self.aspect {
            Simple => Continuous,
            Continuous => Perfect,
            Perfect => PerfectContinuous,
            PerfectContinuous => Simple,
        }
    }

    pub fn scroll_time(&mut self) {
        use Time::*;
        self.time = match self.time {
            Present => Past,
            Past => Future,
            Future => Present,
        }
    }

    fn verb_phrase(v: &Verb, time: &Time, aspect: &Aspect) -> String {
        use {Aspect::*, Time::*};
        match (time, aspect) {
            (Present, Simple) => v.third_singular.clone(),
            (Past, Simple) => v.past.clone(),
            (Future, Simple) => format!("will {}", v.base),
            (Present, Continuous) => format!("is {}", v.ing),
            (Past, Continuous) => format!("was {}", v.ing),
            (Future, Continuous) => format!("will be {}", v.ing),
            (Present, Perfect) => format!("has {}", v.past_participle),
            (Past, Perfect) => format!("had {}", v.past_participle),
            (Future, Perfect) => format!("will have {}", v.past_participle),
            (Present, PerfectContinuous) => format!("has been {}", v.ing),
            (Past, PerfectContinuous) => format!("had been {}", v.ing),
            (Future, PerfectContinuous) => format!("will have been {}", v.ing),
        }
    }
}