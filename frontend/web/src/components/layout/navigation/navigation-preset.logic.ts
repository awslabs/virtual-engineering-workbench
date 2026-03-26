const LOCAL_STORAGE_KEY = 'ExpandedNavGroup';

export class NavigationPreset {
  expandedObj: { [key: string]: boolean };
  constructor() {
    const expandedObj = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (expandedObj) {
      this.expandedObj = JSON.parse(expandedObj);
    } else {
      this.expandedObj = {};
    }
  }

  setItem(navItemKey: string, value: boolean) {
    this.expandedObj[navItemKey] = value;
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(this.expandedObj));
  }
  getItem(navItemKey: string) {
    return this.expandedObj[navItemKey] || false;
  }

  static instance?: NavigationPreset;
  static getInstance(): NavigationPreset {
    if (this.instance) {
      return this.instance;
    }
    this.instance = new NavigationPreset();
    return this.instance;

  }
}
