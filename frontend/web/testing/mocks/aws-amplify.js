const Hub = {
  listen: jest.fn()
}

const Auth = {
  currentSession: () => Promise.reject()
}

const API = {
  post: () => Promise.resolve()
}

export { Hub, Auth, API };
