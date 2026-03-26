export const downloadFile = (url: string, fileName: string) => {
  return fetch(url)
    .then((response) => {
      if (response.ok) {
        return response.blob();
      }
      throw new Error('Unable to download the file');
    })
    .then((blob) => {
      const url = window.URL.createObjectURL(new Blob([blob]));
      const link = document.createElement('a');
      link.href = url;
      link.download = fileName;
      document.body.appendChild(link);

      link.click();

      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    });
};
