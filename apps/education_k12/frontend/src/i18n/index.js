import { createI18n } from 'vue-i18n'
import en from './locales/en.json'
import ar from './locales/ar.json'
import { directionFor } from './direction'

export const i18n = createI18n({
  legacy: false,
  locale: 'en',
  fallbackLocale: 'en',
  messages: { en, ar },
})

export function setLocale(locale) {
  i18n.global.locale.value = locale
  document.documentElement.setAttribute('lang', locale)
  document.documentElement.setAttribute('dir', directionFor(locale))
}
