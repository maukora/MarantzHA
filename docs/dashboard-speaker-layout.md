# Speaker layout on a dashboard

`sensor.hi_fi_av_20_speaker_layout` holds the layout (for example `7.4.4`: ear-level speakers, subwoofer
outputs, heights). Its `speakers` attribute lists each configured speaker with:

| Key | Meaning |
|---|---|
| `channel`, `name`, `group` | `FL`, "Front left", `front` / `center` / `surround` / `surround_back` / `height` / `subwoofer` |
| `azimuth`, `elevation` | Nominal Dolby/ITU angles in degrees (0 = front, negative = left). Not measured |
| `x`, `y` | The same angle on a unit circle around the listener (x right, y front) |
| `playing` | Playing right now (from the receiver's active speaker map), `null` until the first update |
| `level_db`, `delay_ms`, `relative_distance_m` | Dirac level, delay and extra distance vs the closest speaker |

Both cards below use only built-in cards (no custom cards to install). Paste each into a dashboard
with **Add card → Manual**.

## 1. Table (live, shows what plays)

```yaml
type: markdown
title: Speakers
content: >-
  {% set l = 'sensor.hi_fi_av_20_speaker_layout' %}
  **{{ states(l) }}** · {{ state_attr(l, 'playing_count') }} of
  {{ state_attr(l, 'speaker_count') }} playing

  | | Speaker | Level | Delay | Extra distance |
  |:-:|---|--:|--:|--:|
  {% for s in state_attr(l, 'speakers') or [] -%}
  | {{ '🔊' if s.playing else ('·' if s.playing is false else '?') }} | {{ s.name }} | {{ s.level_db }} dB | {{ s.delay_ms | default('–') }} ms | {{ s.relative_distance_m | default('–') }} m |
  {% endfor %}
```

## 2. Room plan with delays

Speakers sit at their nominal angles: ear-level ones on the outer ring, heights on the inner dashed
ring, subwoofers in the corners. The top bar is the screen. Each label shows the speaker's delay.
Tap a label to open that sensor.

```yaml
type: picture-elements
image: "data:image/svg+xml;utf8,%3Csvg%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20viewBox%3D%220%200%20400%20400%22%3E%3Crect%20x%3D%2210%22%20y%3D%2210%22%20width%3D%22380%22%20height%3D%22380%22%20rx%3D%2216%22%20fill%3D%22none%22%20stroke%3D%22%23888%22%20stroke-width%3D%223%22/%3E%3Ccircle%20cx%3D%22200%22%20cy%3D%22200%22%20r%3D%2288%22%20fill%3D%22none%22%20stroke%3D%22%23888%22%20stroke-dasharray%3D%226%206%22/%3E%3Crect%20x%3D%22120%22%20y%3D%2214%22%20width%3D%22160%22%20height%3D%2210%22%20fill%3D%22%23888%22/%3E%3Ccircle%20cx%3D%22200%22%20cy%3D%22200%22%20r%3D%2210%22%20fill%3D%22%2303a9f4%22/%3E%3C/svg%3E"
elements:
  - type: state-label
    entity: sensor.hi_fi_av_20_front_left_delay
    prefix: "FL "
    style: {left: "31.0%", top: "17.1%", font-size: 12px, background: "var(--card-background-color)", border-radius: 6px, padding: 2px 4px}
  - type: state-label
    entity: sensor.hi_fi_av_20_front_right_delay
    prefix: "FR "
    style: {left: "69.0%", top: "17.1%", font-size: 12px, background: "var(--card-background-color)", border-radius: 6px, padding: 2px 4px}
  - type: state-label
    entity: sensor.hi_fi_av_20_center_delay
    prefix: "C "
    style: {left: "50.0%", top: "12.0%", font-size: 12px, background: "var(--card-background-color)", border-radius: 6px, padding: 2px 4px}
  - type: state-label
    entity: sensor.hi_fi_av_20_surround_left_delay
    prefix: "SL "
    style: {left: "12.6%", top: "56.6%", font-size: 12px, background: "var(--card-background-color)", border-radius: 6px, padding: 2px 4px}
  - type: state-label
    entity: sensor.hi_fi_av_20_surround_right_delay
    prefix: "SR "
    style: {left: "87.4%", top: "56.6%", font-size: 12px, background: "var(--card-background-color)", border-radius: 6px, padding: 2px 4px}
  - type: state-label
    entity: sensor.hi_fi_av_20_surround_back_left_delay
    prefix: "SBL "
    style: {left: "28.2%", top: "81.1%", font-size: 12px, background: "var(--card-background-color)", border-radius: 6px, padding: 2px 4px}
  - type: state-label
    entity: sensor.hi_fi_av_20_surround_back_right_delay
    prefix: "SBR "
    style: {left: "71.8%", top: "81.1%", font-size: 12px, background: "var(--card-background-color)", border-radius: 6px, padding: 2px 4px}
  - type: state-label
    entity: sensor.hi_fi_av_20_front_height_left_delay
    prefix: "FHL "
    style: {left: "35.9%", top: "33.1%", font-size: 12px, background: "var(--card-background-color)", border-radius: 6px, padding: 2px 4px}
  - type: state-label
    entity: sensor.hi_fi_av_20_front_height_right_delay
    prefix: "FHR "
    style: {left: "64.1%", top: "33.1%", font-size: 12px, background: "var(--card-background-color)", border-radius: 6px, padding: 2px 4px}
  - type: state-label
    entity: sensor.hi_fi_av_20_rear_height_left_delay
    prefix: "RHL "
    style: {left: "35.9%", top: "66.9%", font-size: 12px, background: "var(--card-background-color)", border-radius: 6px, padding: 2px 4px}
  - type: state-label
    entity: sensor.hi_fi_av_20_rear_height_right_delay
    prefix: "RHR "
    style: {left: "64.1%", top: "66.9%", font-size: 12px, background: "var(--card-background-color)", border-radius: 6px, padding: 2px 4px}
  - type: state-label
    entity: sensor.hi_fi_av_20_subwoofer_delay
    prefix: "SW "
    style: {left: "35.0%", top: "8.7%", font-size: 12px, background: "var(--card-background-color)", border-radius: 6px, padding: 2px 4px}
  - type: state-label
    entity: sensor.hi_fi_av_20_subwoofer_2_delay
    prefix: "SW2 "
    style: {left: "65.0%", top: "8.7%", font-size: 12px, background: "var(--card-background-color)", border-radius: 6px, padding: 2px 4px}
  - type: state-label
    entity: sensor.hi_fi_av_20_subwoofer_3_delay
    prefix: "SW3 "
    style: {left: "35.0%", top: "91.3%", font-size: 12px, background: "var(--card-background-color)", border-radius: 6px, padding: 2px 4px}
  - type: state-label
    entity: sensor.hi_fi_av_20_subwoofer_4_delay
    prefix: "SW4 "
    style: {left: "65.0%", top: "91.3%", font-size: 12px, background: "var(--card-background-color)", border-radius: 6px, padding: 2px 4px}
```

Possible next step: a custom card (for example `custom:button-card`) can colour each speaker by its
`playing` value. The data is already in the attribute.
