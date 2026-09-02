# Maintainer: Gabrigas artroxgabriel@gmail.com
pkgname=ghpdf-mermaid
pkgver=1.0.0
pkgrel=1
pkgdesc="A fork of ghpdf (Markdown to PDF converter with GitHub-style rendering) with Mermaid support"
arch=('any')
url="https://github.com/ArtroxGabriel/ghpdf-mermaid"
license=('MIT')
depends=(
    'python>=3.11'
    'python-markdown>=3.7'
    'python-weasyprint>=62.0'
    'python-pygments>=2.18.0'
    'python-typer>=0.12.0'
    'pango'
)
optdepends=(
    'mermaid-cli: for rendering Mermaid diagram blocks'
)
makedepends=(
    'git'
    'python-build'
    'python-installer'
    'python-hatchling'
    'python-wheel'
)
provides=('ghpdf')
conflicts=('ghpdf')
source=("git+https://github.com/ArtroxGabriel/ghpdf-mermaid.git#tag=v${pkgver}")
sha256sums=('SKIP')

build() {
    cd "${srcdir}/${pkgname}"
    python -m build --wheel --no-isolation
}

package() {
    cd "${srcdir}/${pkgname}"
    python -m installer --destdir="${pkgdir}" dist/*.whl
    install -Dm644 README.md "${pkgdir}/usr/share/doc/${pkgname}/README.md"
}
