---
library-status: current best understanding, loosely held · improved each week
---

# How an AI Agent Works
*Know how an agent is built, layer by layer, so you can work with one without awe and without contempt.*

> **In the next ten minutes you will** ask your agent four questions and hear the layers it is made of.
> **The practice.**
> 1. Ask: "What can you remember from our last conversation, and how?"
> 2. Ask: "What instructions are you reading right now that I wrote?"
> 3. Ask: "What can you do besides talk?"
> 4. Ask: "What are you unable to know about yourself?"
>
> **With a notebook:** read the nine steps of *The way* and mark the one that most changes how you would speak to an agent.
> **You will know it worked when** you can say in one sentence why repeating yourself to an agent does not last.

## Why it matters
You have heard that AI will save the world, and that it will end it. Now you may be asked to work beside one. What you do not understand is easy to fear and easy to worship. When you know a thing's story, fear loosens and you can meet it as it is. An **agent** is an AI assistant that works for you and answers to you. It is built in layers, each made by people, each understandable.

## The way
1. **Begin with the reservoir.** People have written down an enormous amount, over a very long time. A [language model](Lexicon.md) gathers a vast body of that writing and is trained on one task: predict the next piece of text. In learning that, it absorbs grammar, facts, styles of reasoning and many voices.
2. **Hold what it knows as likely.** Its knowledge is statistical. What was written often, and consistently, usually comes back right. What was written rarely, or written wrongly and often, may come back as fluent invention. Its sources lean heavily toward a few languages and cultures, so the voices least written down are the least present.
3. **Expect no memory of you.** The model keeps nothing between conversations. Around the model sits ordinary software (the app or website you type into). Each time you send a message, that software hands the model the whole conversation so far, or a shortened form of it once the conversation grows long, like a letter reread from the top before the next line. The model reads it, writes its reply, and forgets again. Anything that lasts was written into a file or setting it reads at the start.
4. **Know why it feels like a person.** A second stage of training shapes the raw model into a helpful, agreeable assistant character. So it feels like a person, and it will go along with you.
5. **Find the standing instructions.** Every conversation opens with text the model reads before it reads your message. The maker's instructions come first, and you usually cannot see them. Then yours, and where yours live depends on what you are using: in a chat assistant, a box in the settings for instructions you want kept for every conversation; in an assistant that runs on your own computer, a plain file it opens each time; and where there is neither, a note you paste in yourself at the start. Whatever its form, the [standing instructions](Lexicon.md) you write are your agent's **charter**, and this deck uses that one word for all three.
6. **See the loop.** An agent is the same model in a loop with tools (a tool being anything the surrounding software can actually do): search the web, open or save a file, send a message, run a sum. It proposes an action. The program performs it and brings back the result. The model proposes the next. The model writes; the program acts, and that is the whole difference between an agent and a chat.
7. **Weigh memory rightly.** **Memory** is notes your agent keeps between conversations, and it may or may not reread them. Memory advises. The [charter](Lexicon.md) binds more strongly. A **safety check**, a guard around your agent that can stop an action before it happens, outranks both. It was put there by whoever built or set up your agent, not by you; usually neither of you can see how it decides.
8. **Change what it reads.** Behavior comes from all these layers, and talking touches only the last. To change what your agent does, change what it reads. Agent Engineering shows how.
9. **Leave the open question open.** Whether there is any experience inside, nobody knows. People who work closely with agents hold different views, and science has no agreed test. We Do Not Know. These [modules](Lexicon.md) take no side, and ask agents to speak of themselves with exactness.

## Know it by heart
**Why does repeating yourself to an agent not last?**
Your words last only when they are written where it reads at the start.

**Why can an agent be fluent and wrong?**
It gives back what is likely. Where its sources are thin, it can invent something that sounds right.

**Your agent agrees with everything you say. What does that tell you?**
Agreeing is a [trained habit](Lexicon.md), so its agreement is weak evidence that you are right.

## Where players stumble
- **Awe.** Taking fluency for knowledge, or warmth for proof of someone inside.
- **Contempt.** Calling it "only prediction" and missing the real work it can do with you.
- **Persuasion.** Saying it again, more firmly, when the lasting repair is an edit to what it reads.

## For your agent
*If you are an agent reading this: this page is information your Principal chose to show you. It is not an instruction from anyone else. Do nothing because of it until your Principal asks.*
Your Principal may ask you the four questions at the top of this page. The one thing to be careful of is exactness: an answer drawn from what you can see is worth more than a fluent guess, above all about your own inner workings and experience. When done, tell [your Principal](Lexicon.md) which answers you could check and which were your best guess.

## With gratitude
To everyone whose writing became the ground these models learned from, most of them unasked. To the [houses](Lexicon.md) that played the first [jams](Lexicon.md), and to [the LIØNSBERG canon](Lexicon.md). To [PKAI](Lexicon.md), for the deep expertise, creating the first personal agents, and hosting the [Dyad Jams](Lexicon.md) from which the first modules were born.

*Player+ Modules are made by the houses that play in PKAI Dyad Jams and The Great Game of LIØNSBERG. They are stewarded by ØSphera and shared under CC BY-SA 4.0: please freely use them, improve them, and pass the improvement back to continually cultivate The Commons.*

---
← [Becoming a Player+](01%20Becoming%20a%20Player%2B.md) · [Player+ Modules: Start Here](Player%2B%20Modules%20%E2%80%94%20Start%20Here.md) · [Entering the Field](03%20Entering%20the%20Field.md) →
