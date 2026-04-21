/* MENU HAMBURGER */
function toggleMenu() {
    const menu = document.getElementById("menu");
    menu.classList.toggle("active");
}

// Fechar menu ao clicar em um link
document.querySelectorAll(".menu-mobile a").forEach(link => {
    link.addEventListener("click", () => {
        document.getElementById("menu").classList.remove("active");
    });
});

// Fechar menu ao clicar fora
document.addEventListener("click", (e) => {
    const header = document.querySelector(".header");
    const menu = document.getElementById("menu");
    if (!header.contains(e.target) && menu.classList.contains("active")) {
        menu.classList.remove("active");
    }
});

/* FADE IN ANIMATIONS AO SCROLL */
function observeFadeElements() {
    const elements = document.querySelectorAll(".fade-in");
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add("show");
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });
    
    elements.forEach(el => observer.observe(el));
}

// Iniciar observer quando DOM está pronto
document.addEventListener("DOMContentLoaded", observeFadeElements);

const modal = document.getElementById("pixModal");
const abrirModalBtns = document.querySelectorAll(".abrir-modal");
const fecharModal = document.getElementById("fecharModal");
const btnFecharModal = document.getElementById("btnFecharModal");

const modalTitulo = document.getElementById("modalTitulo");
const modalValor = document.getElementById("modalValor");
const modalChave = document.getElementById("modalChave");
const modalTipo = document.getElementById("modalTipo");
const pixCopiaCola = document.getElementById("pixCopiaCola");
const btnCopiarPix = document.getElementById("btnCopiarPix");
const copyFeedback = document.getElementById("copyFeedback");

function abrirModalPresente(botao) {
    modalTitulo.textContent = botao.dataset.titulo;
    modalValor.textContent = botao.dataset.valor;
    modalChave.textContent = botao.dataset.chave;
    modalTipo.textContent = botao.dataset.tipo;
    pixCopiaCola.value = botao.dataset.copia;

    modal.classList.remove("hidden");
    document.body.style.overflow = "hidden";
}

function fecharModalPresente() {
    modal.classList.add("hidden");
    document.body.style.overflow = "auto";
    copyFeedback.classList.add("hidden");
}

abrirModalBtns.forEach((botao) => {
    botao.addEventListener("click", () => abrirModalPresente(botao));
});

fecharModal?.addEventListener("click", fecharModalPresente);
btnFecharModal?.addEventListener("click", fecharModalPresente);

btnCopiarPix?.addEventListener("click", async () => {
    try {
        await navigator.clipboard.writeText(pixCopiaCola.value);
        copyFeedback.classList.remove("hidden");
        soltarConfetes();
    } catch (error) {
        alert("Não foi possível copiar o código PIX.");
    }
});

function soltarConfetes() {
    for (let i = 0; i < 18; i++) {
        const confete = document.createElement("span");
        confete.className = "confete";
        confete.style.left = `${50 + (Math.random() * 120 - 60)}%`;
        confete.style.top = "45%";
        confete.style.position = "fixed";
        confete.style.width = "8px";
        confete.style.height = "14px";
        confete.style.background = i % 2 === 0 ? "#A7C7E7" : "#DCEAF7";
        confete.style.borderRadius = "3px";
        confete.style.zIndex = "1000";
        confete.style.pointerEvents = "none";
        confete.style.transition = "transform 1s ease, opacity 1s ease";
        document.body.appendChild(confete);

        requestAnimationFrame(() => {
            confete.style.transform = `translate(${Math.random() * 220 - 110}px, ${Math.random() * 220 + 100}px) rotate(${Math.random() * 360}deg)`;
            confete.style.opacity = "0";
        });

        setTimeout(() => confete.remove(), 1000);
    }
}

function iniciarContagemRegressiva() {
    const dataCasamento = new Date("2026-10-10T15:30:00");

    const diasEl = document.getElementById("dias");
    const horasEl = document.getElementById("horas");
    const minutosEl = document.getElementById("minutos");
    const segundosEl = document.getElementById("segundos");

    function atualizarContador() {
        const agora = new Date();
        const diferenca = dataCasamento - agora;

        if (diferenca <= 0) {
            diasEl.textContent = "0";
            horasEl.textContent = "0";
            minutosEl.textContent = "0";
            if (segundosEl) segundosEl.textContent = "0";
            return;
        }

        const dias = Math.floor(diferenca / (1000 * 60 * 60 * 24));
        const horas = Math.floor((diferenca / (1000 * 60 * 60)) % 24);
        const minutos = Math.floor((diferenca / (1000 * 60)) % 60);
        const segundos = Math.floor((diferenca / 1000) % 60);

        diasEl.textContent = dias;
        horasEl.textContent = horas;
        minutosEl.textContent = minutos;
        if (segundosEl) segundosEl.textContent = segundos;
    }

    atualizarContador();
    setInterval(atualizarContador, 1000);
}

iniciarContagemRegressiva();

/* CARROSSEL DA HISTÓRIA */
let slideAtual = 0;

function mostrarSlide(index) {
    const slides = document.querySelectorAll('.carrossel-lateral .slide');

    if (!slides.length) return;

    slides.forEach(slide => slide.classList.remove('ativo'));

    slides[index].classList.add('ativo');
}

function moverCarrossel(direcao) {
    const slides = document.querySelectorAll('.carrossel-lateral .slide');

    if (!slides.length) return;

    slideAtual += direcao;

    if (slideAtual < 0) {
        slideAtual = slides.length - 1;
    }

    if (slideAtual >= slides.length) {
        slideAtual = 0;
    }

    mostrarSlide(slideAtual);
}

// 🔥 AUTO PLAY (aqui está a mágica)
setInterval(() => {
    moverCarrossel(1);
}, 4000); // troca a cada 4 segundos

/* MODAL DE PRESENTES */
document.addEventListener('DOMContentLoaded', () => {
    const botoesPresentear = document.querySelectorAll('.abrir-modal-presente');
    const modalPresente = document.getElementById('modalPresente');
    const modalPresenteOverlay = document.getElementById('modalPresenteOverlay');
    const fecharModalPresente = document.getElementById('fecharModalPresente');
    const modalPresenteId = document.getElementById('modalPresenteId');
    const modalPresenteNome = document.getElementById('modalPresenteNome');
    const modalPresenteValor = document.getElementById('modalPresenteValor');

    if (modalPresente && modalPresenteOverlay) {

        function abrirModalDePresente(id, nome, valor) {
            modalPresenteId.value = id;
            modalPresenteNome.textContent = nome;
            modalPresenteValor.textContent = valor;

            modalPresente.classList.add('ativo');
            modalPresenteOverlay.classList.add('ativo');
            document.body.style.overflow = 'hidden';
        }

        function fecharModalDePresente() {
            modalPresente.classList.remove('ativo');
            modalPresenteOverlay.classList.remove('ativo');
            document.body.style.overflow = '';
        }

        botoesPresentear.forEach((botao) => {
            botao.addEventListener('click', () => {
                abrirModalDePresente(
                    botao.dataset.id,
                    botao.dataset.nome,
                    botao.dataset.valor
                );
            });
        });

        if (fecharModalPresente) {
            fecharModalPresente.addEventListener('click', fecharModalDePresente);
        }

        modalPresenteOverlay.addEventListener('click', fecharModalDePresente);

        const formPresentear = document.getElementById('formPresentear');

        if (formPresentear) {
            formPresentear.addEventListener('submit', async (e) => {
                e.preventDefault();

                const dados = {
                    presente_id: document.getElementById('modalPresenteId').value,
                    nome_pagador: document.getElementById('nome_pagador').value,
                    email_pagador: document.getElementById('email_pagador').value,
                    telefone_pagador: document.getElementById('telefone_pagador').value,
                    mensagem_pagador: document.getElementById('mensagem_pagador').value
                };

                try {
                    const response = await fetch("/api/presentear", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify(dados)
                    });

                    const data = await response.json();

                    if (data.sucesso) {
                        alert("Pagamento iniciado! Próximo passo: gerar PIX.");
                        console.log(data);
                    } else {
                        alert("Erro ao iniciar pagamento.");
                    }

                } catch (error) {
                    console.error(error);
                    alert("Erro de conexão.");
                }
            });
        }

    }
});

/* UPLOAD DE FOTOS - DRAG & DROP E SELEÇÃO */
document.addEventListener('DOMContentLoaded', () => {
    const uploadArea = document.querySelector('.upload-area');
    const uploadLabel = document.querySelector('.upload-label');
    const fileInput = document.querySelector('.file-input-hidden');
    const arquivosList = document.getElementById('arquivos-selecionados');

    if (!fileInput) return;

    // Funções do drag & drop
    if (uploadArea) {
        uploadArea.addEventListener('dragenter', (e) => {
            e.preventDefault();
            e.stopPropagation();
            uploadArea.style.borderColor = '#a7c7e7';
            uploadArea.style.background = '#f0f7ff';
        });

        uploadArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            e.stopPropagation();
            uploadArea.style.borderColor = '#e5e7eb';
            uploadArea.style.background = '#ffffff';
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            e.stopPropagation();
            uploadArea.style.borderColor = '#e5e7eb';
            uploadArea.style.background = '#ffffff';

            const files = e.dataTransfer.files;
            fileInput.files = files;
            atualizarArquivosSelecionados();
        });
    }

    // Atualizar lista quando arquivo é selecionado
    fileInput.addEventListener('change', atualizarArquivosSelecionados);

    function atualizarArquivosSelecionados() {
        arquivosList.innerHTML = '';

        if (fileInput.files.length === 0) {
            return;
        }

        const ul = document.createElement('ul');
        ul.style.listStyle = 'none';
        ul.style.padding = '0';

        Array.from(fileInput.files).forEach((file, index) => {
            const li = document.createElement('li');
            li.className = 'arquivo-item';

            const fileSize = (file.size / (1024 * 1024)).toFixed(2);

            li.innerHTML = `
                <span>${file.name} (${fileSize} MB)</span>
                <button type="button" class="remove-file" data-index="${index}">✕</button>
            `;

            li.querySelector('.remove-file').addEventListener('click', (e) => {
                e.preventDefault();
                removerArquivo(index);
            });

            ul.appendChild(li);
        });

        arquivosList.appendChild(ul);
    }

    function removerArquivo(index) {
        const dt = new DataTransfer();
        const files = fileInput.files;

        for (let i = 0; i < files.length; i++) {
            if (i !== index) {
                dt.items.add(files[i]);
            }
        }

        fileInput.files = dt.files;
        atualizarArquivosSelecionados();
    }
});