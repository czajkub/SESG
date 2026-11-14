use color_eyre::Result;
use rand::seq::IndexedRandom;
use crate::words::{read_nouns, read_verbs, Noun, Verb};

#[derive(Debug)]
pub struct App {
    pub should_quit: bool,

    nouns: Vec<Noun>,
    verbs: Vec<Verb>,

    pub time: Time,
    pub aspect: Aspect,

    // alternative is affirmative
    pub question: bool,
    pub negative: bool,

    pub sentences: Vec<String>,

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

pub struct VerbPhrase {
    operator: Option<String>, // "has", "was", "will"; None for present/past simple
    rest: String,             // "eaten", "been eating", "have been eating"; or "eats"/"ate"
}
impl VerbPhrase{
    pub fn new(op: Option<String>, rest: String) -> Self {
        Self { operator: op, rest: rest }
    }
}

impl std::fmt::Display for VerbPhrase {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match &self.operator {
            Some(op) => write!(f, "{} {}", op, self.rest),
            None => write!(f, "{}", self.rest),
        }
    }
}

impl App {
    pub fn new() -> Result<Self> {
        Ok(Self {
            should_quit: false,
            nouns: read_nouns()?,
            verbs: read_verbs()?,
            time: Time::default(),
            aspect: Aspect::default(),
            question: false,
            negative: false,
            sentences: vec!["The Example Is Sentenced".to_string()],
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

    pub fn switch_sentence_type(&mut self) {
        self.question = !self.question
    }
    
    pub fn switch_negative(&mut self) {
        self.negative = !self.negative
    }

    pub fn generate_sentence(&mut self) {
        let mut rng = rand::rng();

        let subject = self.nouns.choose(&mut rng)
                    .unwrap_or(self.nouns.first().unwrap())
                    .noun.clone();
        
        let object = self.nouns.choose(&mut rng)
                    .unwrap_or(self.nouns.first().unwrap())
                    .noun.clone();
        
        let verb = self.verbs.choose(&mut rng)
                    .unwrap_or(self.verbs.first().unwrap());
        let verb_phrase = App::verb_phrase(verb, &self.time, &self.aspect, self.question || self.negative);

        let rest = &verb_phrase.rest;
        let sentence = match (self.question, self.negative) {
            (false, false) => format!("The {subject} {verb_phrase} the {object}."),
            (question, negative) => {
                let op = verb_phrase
                    .operator
                    .as_deref()
                    .expect("questions/negatives always have an operator");
                match (question, negative) {
                    (false, true) => format!("The {subject} {op} not {rest} the {object}."),
                    (true, false) => format!("{} the {subject} {rest} the {object}?", capitalize(op)),
                    (true, true) => format!("{} the {subject} {rest} the {object}?", capitalize(&negate_operator(op))),
                    (false, false) => unreachable!("handled by the outer match"),
                }
            }
        };
        self.sentences.push(sentence)
    }



    fn verb_phrase(v: &Verb, time: &Time, aspect: &Aspect, needs_do: bool) -> VerbPhrase {
        use {Aspect::*, Time::*};
        match (time, aspect) {
            (Present, Simple) if needs_do => VerbPhrase::new(Some("does".into()), v.base.clone()),
            (Past, Simple) if needs_do => VerbPhrase::new(Some("did".into()), v.base.clone()),
            (Present, Simple) => VerbPhrase::new(None, v.third_singular.clone()),
            (Past, Simple) => VerbPhrase::new(None, v.past.clone()),
            (Future, Simple) => VerbPhrase::new(Some("will".into()), v.base.clone()),
            (Present, Continuous) => VerbPhrase::new(Some("is".into()), v.ing.clone()),
            (Past, Continuous) => VerbPhrase::new(Some("was".into()), v.ing.clone()),
            (Future, Continuous) => VerbPhrase::new(Some("will".into()), format!("be {}", v.ing)),
            (Present, Perfect) => VerbPhrase::new(Some("has".into()), v.past_participle.clone()),
            (Past, Perfect) => VerbPhrase::new(Some("had".into()), v.past_participle.clone()),
            (Future, Perfect) => VerbPhrase::new(Some("will".into()), format!("have {}", v.past_participle)),
            (Present, PerfectContinuous) => VerbPhrase::new(Some("has".into()), format!("been {}", v.ing)),
            (Past, PerfectContinuous) => VerbPhrase::new(Some("had".into()), format!("been {}", v.ing)),
            (Future, PerfectContinuous) => VerbPhrase::new(Some("will".into()), format!("have been {}", v.ing)),
        }
    }
}


fn capitalize(s: &str) -> String {
    let mut chars = s.chars();
    match chars.next() {
        Some(first) => first.to_uppercase().chain(chars).collect(),
        None => String::new(),
    }
}

fn negate_operator(op: &str) -> String {
    match op {
        "will" => "won't".to_string(),
        _ => format!("{op}n't"),
    }
}
