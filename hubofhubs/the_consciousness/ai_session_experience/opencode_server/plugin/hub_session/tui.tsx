import { Plugin } from "@opencode/plugin/tui"

// What only the hub knows, in the client's own slots. The hub server puts it in the session's metadata (`hub`), already worded by the hub's shared presentation rules; this file only places it.
//   session.composer.top  one quiet line above the prompt, at every width: who the work serves, who the AI acts for, a spend note (only once a ceiling is half used or a cost is under a cent),
//                         the metric before and after at the end, the consumer's own short lines (`header`), and the person's notes as sent, then taken up
//   sidebar.content       the same in full, in the client's sidebar (the client shows it only on a wide terminal)
//   session.panel         the structure overview with spend and time against the ceilings, opened by the /structure command
type Note = { text: string; taken_up: boolean }
type Hub = {
  serves?: string
  milestone?: string
  acting_for?: string
  quiet?: string
  spend_full?: string
  time_full?: string
  metric?: string
  helpers?: number
  corrections?: Note[]
  structure?: string[]
  authority?: string[]
  header?: string[]
}

export default Plugin.define({
  id: "hub.session",
  setup(context) {
    const hub = (sessionID?: string): Hub => {
      const meta = sessionID ? (context.data.session.get(sessionID)?.metadata as { hub?: Hub } | undefined) : undefined
      return meta?.hub ?? {}
    }
    const muted = () => context.theme.text.muted
    const line = (sessionID?: string) => {
      const h = hub(sessionID)
      const notes = (h.corrections ?? []).map((n) => (n.taken_up ? "taken up: " : "sent: ") + n.text)
      return [h.serves ? "serves " + h.serves : "", h.acting_for ? "for " + h.acting_for : "", h.quiet ?? "", h.metric ?? "", ...(h.header ?? []), ...notes].filter((part) => part).join(" · ")
    }

    context.ui.slot({
      append: "session.composer.top",
      render: (props) => (line(props.sessionID) ? <text fg={muted()}>{line(props.sessionID)}</text> : null),
    })

    context.ui.slot({
      append: "sidebar.content",
      render: (props) => (
        <box>
          {hub(props.sessionID).serves ? <text fg={context.theme.text.base}>{"Serves " + hub(props.sessionID).serves}</text> : null}
          {hub(props.sessionID).milestone ? <text fg={muted()}>{hub(props.sessionID).milestone}</text> : null}
          {hub(props.sessionID).acting_for ? <text fg={muted()}>{"for " + hub(props.sessionID).acting_for}</text> : null}
          {hub(props.sessionID).metric ? <text fg={muted()}>{hub(props.sessionID).metric}</text> : null}
          {(hub(props.sessionID).header ?? []).map((row) => (
            <text fg={muted()}>{row}</text>
          ))}
        </box>
      ),
    })

    context.ui.slot({
      append: "session.panel",
      render: (props) =>
        props.name === "hub.structure" ? (
          <box>
            <text fg={context.theme.text.base}>{"structure (" + (hub(props.sessionID).helpers ?? 0) + " helpers)"}</text>
            {(hub(props.sessionID).structure ?? []).map((row) => (
              <text fg={muted()}>{row}</text>
            ))}
            <text fg={muted()}>{(hub(props.sessionID).spend_full ?? "") + " · " + (hub(props.sessionID).time_full ?? "")}</text>
            {(hub(props.sessionID).authority ?? []).map((row) => (
              <text fg={muted()}>{row}</text>
            ))}
          </box>
        ) : null,
    })

    context.keymap.layer(() => ({
      mode: "global",
      commands: [
        {
          id: "hub.structure",
          title: "Structure overview",
          group: "Hub",
          palette: true,
          slash: { name: "structure" },
          run: () => {
            context.ui.panel.open("hub.structure")
          },
        },
      ],
    }))
  },
})
