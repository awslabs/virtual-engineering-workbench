import { LoginRequest, LoginResponse, ProvisionedProductLoginType } from '.';
import { i18n } from './translations';

export class RDPLoginType extends ProvisionedProductLoginType {
  doLoginPrivate(loginRequest: LoginRequest): Promise<LoginResponse> {
    if (!loginRequest.connectAddress) {
      throw Error(i18n.errorConnectionAddress);
    }

    const username = loginRequest.user?.userId.toUpperCase() || '-';
    const rdpBody =
      'screen mode id:i:2\n' +
      `use multimon:i:${loginRequest.extendToAllMonitors ? '1' : '0'}\n` +
      'desktopwidth:i:1920\n' +
      'desktopheight:i:1080\n' +
      'session bpp:i:16\n' +
      'winposstr:s:0,1,1475,249,2479,982\n' +
      'compression:i:1\n' +
      'keyboardhook:i:2\n' +
      'audiocapturemode:i:0\n' +
      'videoplaybackmode:i:1\n' +
      'connection type:i:6\n' +
      'networkautodetect:i:1\n' +
      'bandwidthautodetect:i:0\n' +
      'displayconnectionbar:i:1\n' +
      'enableworkspacereconnect:i:0\n' +
      'disable wallpaper:i:1\n' +
      'allow font smoothing:i:0\n' +
      'allow desktop composition:i:0\n' +
      'disable full window drag:i:1\n' +
      'disable menu anims:i:1\n' +
      'disable themes:i:1\n' +
      'disable cursor setting:i:0\n' +
      'bitmapcachepersistenable:i:1\n' +
      `full address:s:${loginRequest.connectAddress}\n` +
      'audiomode:i:0\n' +
      'redirectprinters:i:1\n' +
      'redirectcomports:i:0\n' +
      'redirectsmartcards:i:1\n' +
      'redirectclipboard:i:1\n' +
      'redirectposdevices:i:0\n' +
      'autoreconnection enabled:i:1\n' +
      'authentication level:i:2\n' +
      'prompt for credentials:i:0\n' +
      'negotiate security layer:i:1\n' +
      'remoteapplicationmode:i:0\n' +
      'alternate shell:s:\n' +
      'shell working directory:s:\n' +
      'gatewayhostname:s:\n' +
      'gatewayusagemethod:i:4\n' +
      'gatewaycredentialssource:i:4\n' +
      'gatewayprofileusagemethod:i:0\n' +
      'promptcredentialonce:i:0\n' +
      'gatewaybrokeringtype:i:0\n' +
      'use redirection server name:i:0\n' +
      'rdgiskdcproxy:i:0\n' +
      'kdcproxyname:s:\n' +
      'drivestoredirect:s:\n' +
      `username:s:${loginRequest.userDomain.toLocaleUpperCase()}\\${username.toLocaleUpperCase()}`;

    return Promise.resolve({
      type: 'file',
      loginFile: {
        loginFileContent: rdpBody,
        loginFileName: `${this.getLoginFileName(loginRequest.provisionedProduct)}.rdp`,
      }
    });
  }
}