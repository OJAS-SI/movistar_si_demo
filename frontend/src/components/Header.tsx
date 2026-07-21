import type { ConsoleOut, RunOut, ScaleName } from '../api/types'
import { LANGS, type Lang, type StringKey, type T } from '../lib/i18n'
import { Icon, type IconName } from './Icon'

export type TabKey = 'analyst' | 'mgmt' | 'map'

const TABS: { key: TabKey; label: StringKey; icon: IconName }[] = [
  { key: 'analyst', label: 'tab.analyst', icon: 'graph' },
  { key: 'mgmt', label: 'tab.management', icon: 'grid' },
  { key: 'map', label: 'tab.map', icon: 'map' },
]

interface HeaderProps {
  model: ConsoleOut | null
  run: RunOut | null
  scale: ScaleName
  busy: boolean
  tab: TabKey
  onTab: (tab: TabKey) => void
  onScale: (scale: ScaleName) => void
  lang: Lang
  onLang: (lang: Lang) => void
  t: T
}

export function Header({ model, run, scale, busy, tab, onTab, onScale,
                         lang, onLang, t }: HeaderProps) {
  return (
    <header>
      <div className="brand">
        <span className="logo">
          <Icon name="network" />
        </span>
        <div>
          <h1>{model?.title ?? 'Movistar Service Intelligence'}</h1>
          <div className="sub">{t('header.subtitle')}</div>
        </div>
        <span className="synthetic">{t('header.synthetic')}</span>
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
            {t(label)}
          </button>
        ))}
      </nav>

      <div className="config">
        <span>
          <span className={`dot${busy ? ' busy' : ''}`} />
          {t('header.engine')}{' '}
          <b className="mono">{busy ? t('header.engine.running') : t('header.engine.live')}</b>
        </span>

        {/* The run's own description of itself, rather than anything we assume. */}
        {model && <span>{model.config_summary}</span>}
        {run && (
          <span>
            {t('mgmt.seed')} <b className="mono">{run.seed}</b>
          </span>
        )}

        <div className="runctl">
          <div className="seg" role="group" aria-label={t('header.scale')}>
            {(['tiny', 'full'] as ScaleName[]).map((option) => (
              <button
                key={option}
                type="button"
                className={scale === option ? 'on' : ''}
                onClick={() => onScale(option)}
                title={t(option === 'tiny' ? 'header.scale.tiny.tip' : 'header.scale.full.tip')}
              >
                {t(option === 'tiny' ? 'header.scale.tiny' : 'header.scale.full')}
              </button>
            ))}
          </div>

          {/* Language sits beside scale because both re-read the run rather than
              changing what it measured. Switching language never re-runs the engine:
              the verdicts and every number are identical, only the prose is re-rendered. */}
          <div className="seg" role="group" aria-label={t('header.language')}>
            {LANGS.map((option) => (
              <button
                key={option}
                type="button"
                className={lang === option ? 'on' : ''}
                aria-pressed={lang === option}
                onClick={() => onLang(option)}
                title={option === 'en' ? 'English' : 'Español'}
              >
                {option.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      </div>
    </header>
  )
}