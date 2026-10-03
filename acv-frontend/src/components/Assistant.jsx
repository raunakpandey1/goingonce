import { useEffect, useRef } from 'react'
import Icon, { logIcon } from './Icon'

function Step({ line }) {
  const [name, tone] = logIcon(line.icon)
  return (
    <div className="step">
      <div className={`step-icon ${tone}`}><Icon name={name} size={13} stroke={2.5} /></div>
      <div>
        <div className="step-text">
          {line.text}
          {line.ai && <span className="ai-chip"><Icon name="zap" size={9} stroke={3} />AI</span>}
        </div>
        {line.detail && <div className="step-detail">{line.detail}</div>}
      </div>
    </div>
  )
}

// Chat-style panel: the user's request, the agent's live steps, and its questions.
export default function Assistant({ title, intro, run, actions, onAction, doneText, children }) {
  const threadRef = useRef(null)
  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight, behavior: 'smooth' })
  }, [run?.log.length, run?.pending, run?.busy])

  // Split the log into step groups, with the user's button choices in between.
  const segments = []
  if (run) {
    const choices = run.choices || []
    let group = []
    run.log.forEach((line, i) => {
      choices.filter((c) => c.at === i).forEach((c) => {
        if (group.length) segments.push({ steps: group })
        group = []
        segments.push({ choice: c.text })
      })
      group.push(line)
    })
    if (group.length) segments.push({ steps: group })
    choices.filter((c) => c.at >= run.log.length).forEach((c) => segments.push({ choice: c.text }))
  }

  return (
    <aside className="card assistant">
      <div className="assistant-head">
        <div className="bot-avatar"><Icon name="gavel" size={20} stroke={2.2} /></div>
        <div>
          <h3>{title}</h3>
          <div className="status">Online · ACV + Copart</div>
        </div>
      </div>
      <div className="thread" ref={threadRef}>
        <div className="bubble bot">{intro}</div>
        {run?.userText && <div className="bubble user">{run.userText}</div>}
        {segments.map((seg, i) => seg.choice
          ? <div key={i} className="bubble user">{seg.choice}</div>
          : <div key={i} className="steps">{seg.steps.map((line, j) => <Step key={j} line={line} />)}</div>)}
        {run?.busy && <div className="steps"><div className="typing"><span /><span /><span /></div></div>}
        {run?.pending && !run.busy && actions && (
          <div className="ask">
            <p>{run.pending.question}</p>
            <div className="row">
              {actions.map((a) => (
                <button key={a.label} className={`btn btn-sm ${a.primary ? 'btn-primary' : 'btn-ghost'}`}
                  onClick={() => onAction(a.value, a.choiceText || a.label)}>{a.label}</button>
              ))}
            </div>
          </div>
        )}
        {run && !run.busy && !run.pending && doneText && <div className="done-note"><Icon name="check" size={16} stroke={3} />{doneText}</div>}
        {run?.error && <div className="bubble bot" style={{ color: 'var(--red)' }}>Something went wrong: {run.error}</div>}
      </div>
      <div className="composer">{children}</div>
    </aside>
  )
}
