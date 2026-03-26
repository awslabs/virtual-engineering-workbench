import { CloudFrontRequestEvent, CloudFrontRequestResult } from 'aws-lambda';
import { AuthenticatorInterface } from 'cognito-at-edge';
import { Cookies, Cookie } from 'cognito-at-edge/dist/util/cookie';

interface AuthenticatorWithCookieDeduplicationProps {
  userPoolAppId: string,
}

class AuthenticatorWithCookieDeduplication implements AuthenticatorInterface {

  private readonly _cookieBase: string;

  constructor(
    private readonly _inner: AuthenticatorInterface,
    private readonly _props: AuthenticatorWithCookieDeduplicationProps,
  ) {
    this._cookieBase = `CognitoIdentityServiceProvider.${this._props.userPoolAppId}.`;
  }

  public static decorate(inner: AuthenticatorInterface, props: AuthenticatorWithCookieDeduplicationProps): AuthenticatorInterface {
    return new AuthenticatorWithCookieDeduplication(inner, props);
  }

  async handle(event: CloudFrontRequestEvent): Promise<CloudFrontRequestResult> {
    const { request } = event.Records[0].cf;
    const domain = request.headers.host[0].value;

    if (request.headers.cookie) {
      const cookiesToReset = this._getCookiesToReset(request.headers.cookie);

      if (cookiesToReset.length > 1) {
        return {
          status: '302',
          headers: {
            location: [{
              key: 'Location',
              value: request.uri,
            }],
            // eslint-disable-next-line @typescript-eslint/naming-convention
            'cache-control': [{
              key: 'Cache-Control',
              value: 'no-cache, no-store, max-age=0, must-revalidate',
            }],
            pragma: [{
              key: 'Pragma',
              value: 'no-cache',
            }],
            // eslint-disable-next-line @typescript-eslint/naming-convention
            'set-cookie': cookiesToReset.map(x => ({
              key: 'Set-Cookie',
              value: Cookies.serialize(x.name, '', {
                expires: new Date(Date.now() - 864e+5),
                secure: true,
                path: '/'
              })
            }))
          },
        };
      }
    }

    return this._inner.handle(event);
  }

  private _getCookiesToReset(cookieHeader: Array<{
    key?: string | undefined,
    value: string,
  }>) {
    const cookies = cookieHeader.flatMap(h => Cookies.parse(h.value));

    const cookiesToReset = [
      ...this._getIdTokenCookiesToReset(cookies),
      ...this._getAccessTokenCookiesToReset(cookies),
      ...this._getRefreshTokenCookiesToReset(cookies),
      ...this._getTokenScopesCookiesToReset(cookies),
    ];

    return cookiesToReset;
  }

  private _getIdTokenCookiesToReset(cookies: Cookie[]) {
    const tokenCookieNamePostfixIdToken = '.idToken';
    const idTokenCookies = this._getCookiesWithPostfix(cookies, tokenCookieNamePostfixIdToken);
    return idTokenCookies.length > 1 ? idTokenCookies : [];
  }

  private _getAccessTokenCookiesToReset(cookies: Cookie[]) {
    const tokenCookieNamePostfixAccessToken = '.accessToken';
    const accessTokenCookies = this._getCookiesWithPostfix(cookies, tokenCookieNamePostfixAccessToken);
    return accessTokenCookies.length > 1 ? accessTokenCookies : [];
  }

  private _getRefreshTokenCookiesToReset(cookies: Cookie[]) {
    const tokenCookieNamePostfixRefreshToken = '.refreshToken';
    const refreshTokenCookies = this._getCookiesWithPostfix(cookies, tokenCookieNamePostfixRefreshToken);
    return refreshTokenCookies.length > 1 ? refreshTokenCookies : [];
  }

  private _getTokenScopesCookiesToReset(cookies: Cookie[]) {
    const tokenCookieNamePostfixTokenScopes = '.tokenScopesString';
    const tokenScopeCookies = this._getCookiesWithPostfix(cookies, tokenCookieNamePostfixTokenScopes);
    return tokenScopeCookies.length > 1 ? tokenScopeCookies : [];
  }

  private _getCookiesWithPostfix(cookies: Cookie[], postfix: string): Cookie[] {
    return cookies.filter(x => x.name.startsWith(this._cookieBase) && x.name.endsWith(postfix));
  }
}

export { AuthenticatorWithCookieDeduplication };