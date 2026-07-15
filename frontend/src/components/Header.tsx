import type { ConsoleOut, RunOut, ScaleName } from '../api/types'
import { Icon, type IconName } from './Icon'

export type TabKey = 'analyst' | 'mgmt' | 'map'

const TABS: { key: TabKey; label: string; icon: IconName }[] = [
  { key: 'analyst', label: 'Analyst', icon: 'graph' },
  { key: 'mgmt', label: 'Management', icon: 'grid' },
  { key: 'map', label: 'Map of Spain', icon: 'map' },
]

interface HeaderProps {
  model: ConsoleOut | null
  run: RunOut | null
  scale: ScaleName
  busy: boolean
  tab: TabKey
  onTab: (tab: TabKey) => void
  onScale: (scale: ScaleName) => void
}

export function Header({ model, run, scale, busy, tab, onTab, onScale }: HeaderProps) {
  return (
    <header>
      <div className="brand">
        <span className="logo">
          <Icon name="network" />
        </span>
        <div>
          <h1>{model?.title ?? 'Movistar Service Intelligence'}</h1>
          <div className="sub">Customer Experience Operations Center</div>
        </div>
        <span className="synthetic">Synthetic demo</span>
      </div>

      <nav className="tabs">
        {TABS.map(({ key, label, icon }) => (
          <button
            key={key}
            type="button"
            className={`tab${tab === key ? ' active' : ''}`}
            aria-current={tab === key}
            onClick={() => onTab(key)}
          >
            <Icon name={icon} />
            {label}
          </button>
        ))}
      </nav>

      <div className="config">
        <span>
          <span className={`dot${busy ? ' busy' : ''}`} />
          SI engine <b className="mono">{busy ? 'running' : 'live'}</b>
        </span>

        {/* The run's own description of itself, rather than anything we assume. */}
        {model && <span>{model.config_summary}</span>}
        {run && (
          <span>
            seed <b className="mono">{run.seed}</b>
          </span>
        )}

        <div className="runctl">
          <div className="seg" role="group" aria-label="Network scale">
            {(['tiny', 'full'] as ScaleName[]).map((option) => (
              <button
                key={option}
                type="button"
                className={scale === option ? 'on' : ''}
                onClick={() => onScale(option)}
                title={
                  option === 'tiny'
                    ? 'A small network, a short run — the whole story in a second.'
                    : 'The full six-region network. Slower to compute.'
                }
              >
                {option === 'tiny' ? 'Tiny' : 'Full'}
              </button>
            ))}
          </div>
        </div>
      </div>
    </header>
  )
}