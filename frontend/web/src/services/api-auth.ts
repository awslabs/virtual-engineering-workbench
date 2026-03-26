import { fetchAuthSession } from 'aws-amplify/auth';

export async function getAccessToken() {
  try {
    const session = await fetchAuthSession();
    return session.tokens?.accessToken?.toString() || '';
  } catch {
    return Promise.reject(new Error('Failed to get access token'));
  }
}