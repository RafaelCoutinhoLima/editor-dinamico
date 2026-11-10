# Configuração das cenas do Reel tutorial LoopEdu (fonte: fonte/gravacao.mp4, 1362x596).
# piece: ("src", a, b, fixed)  -> trecho da gravação; fixed=True mantém velocidade normal
#        ("freeze", t, dur)     -> congela o quadro t por dur segundos (câmera continua no relógio t..t+dur)
# cam: (tempo_camera, cx, cy, w, h) em coordenadas da gravação; tempo_camera = tempo da fonte
# caps: (tempo_camera, texto)
SCENES = [
 dict(name="materia", line=1, maxspeed=1.5,
      pieces=[("src",101.6,105.8,False)],
      cam=[(101.6,674,332,1000,330),(105.8,674,332,990,326)],
      caps=[(0,"Digite sua matéria")]),
 dict(name="assuntos", line=2,
      pieces=[("src",108.55,109.95,False),("src",111.6,118.6,False)],
      cam=[(108.55,672,345,1000,500),(112.3,672,345,1000,500),(118.6,672,345,990,495)],
      caps=[(0,"Receba os assuntos sugeridos"),(112.5,"Ou cole a ementa do professor")]),
 dict(name="periodos", line=3,
      pieces=[("src",193.6,198.2,False)],
      cam=[(193.6,797,178,1000,335),(195.7,797,178,1000,335),(196.6,797,428,1000,336),(198.2,797,428,992,333)],
      caps=[(0,"Escolha os períodos do dia"),(196.3,"E os dias da semana")]),
 dict(name="grade", line=4,
      pieces=[("src",210.2,214.6,False)],
      cam=[(210.2,797,255,1000,380),(214.6,797,255,990,376)],
      caps=[(0,"Se preferir, monte seu horário")]),
 dict(name="semana", line=5,
      pieces=[("src",340.0,346.0,False)],
      cam=[(340.0,797,330,1050,470),(346.0,797,330,1040,466)],
      caps=[(0,"Sua semana personalizada")]),
 dict(name="lupe", line=6,
      pieces=[("src",286.5,288.0,False),("src",300.6,304.75,False)],
      cam=[(286.5,681,298,1362,596),(286.9,681,298,1362,596),(287.9,816,298,1092,596),(305.2,816,298,1092,596)],
      caps=[(0,"Tire dúvidas com a Lupe")]),
 dict(name="tutor", line=7,
      pieces=[("src",459.0,465.0,False)],
      cam=[(459.0,680,300,800,480),(465.0,680,300,790,474)],
      caps=[(0,"Estude com o tutor de IA")]),
 dict(name="questao", line=8,
      pieces=[("src",470.0,472.9,False)],
      cam=[(470.0,675,329,1130,534),(472.9,675,329,1122,530)],
      caps=[(0,"Revise com questões")]),
 dict(name="ajuda", line=9,
      pieces=[("src",479.0,483.0,True)],
      cam=[(479.0,681,298,1362,596),(479.48,681,298,1362,596),(479.70,681,298,840,560),(483.0,681,298,820,548)],
      caps=[(0,"Travou? Peça ajuda")]),
 dict(name="correcao", line=10,
      pieces=[("src",485.2,486.6,True),("freeze",486.6,None)],
      cam=[(485.2,502,300,800,520),(485.95,502,300,800,520),(486.5,502,278,800,474),(489.5,502,278,790,468)],
      caps=[(0,"Veja a correção")]),
 dict(name="resumo", line=11,
      pieces=[("src",504.65,507.0,False),("src",523.5,524.28,True),("freeze",524.28,1.4),("src",541.25,542.65,True)],
      cam=[(504.65,675,330,1080,560),(507.0,675,330,1070,555),(523.5,675,330,1080,560),(525.7,675,330,1070,555),(541.25,490,330,720,420),(542.65,490,330,712,416)],
      caps=[(0,"Veja o resumo da aula"),(520.0,"Revisões já na sua semana"),(539.5,"O mapa do que você estudou")]),
 dict(name="conquistas", line=12,
      pieces=[("src",434.0,436.8,False),("freeze",436.8,1.1),("src",443.25,444.62,True),("freeze",444.62,2.6)],
      cam=[(434.0,800,323,1080,546),(434.8,800,323,1080,546),(436.3,797,210,1080,310),(436.8,797,210,1075,308),(437.9,797,210,1070,306),
           (443.25,800,323,1080,546),(444.62,800,323,1080,546),(445.4,1006,400,640,260),(447.2,1006,400,634,258)],
      caps=[(0,"Acompanhe sua evolução"),(443.2,"Ganhe insígnias estudando")],
      spot=(444.9,(905,276,1105,484))),
]
# remendo do indicador de teclado "abc" do sistema (cobre x604-758, y378-532 entre 98,5 e 108,3 s)
PATCH = dict(t0=98.5, t1=108.3, rect=(598,372,764,538), clean_t=97.0)

# dados pessoais da conta de teste (nome "Theo"): preenchidos com a cor das bordas, linha a linha
HIDE = [
 (286.0, 288.5, (16,516,226,572)),   # nome na barra lateral
 (286.0, 288.5, (278,148,522,196)),  # "Boa noite, Theo"
 (300.0, 305.5, (278,148,522,196)),  # "Boa noite, Theo" durante a resposta da Lupe
 (433.9, 437.7, (425,165,640,201)),  # "Theo · Começando" no cartão de nível
 (443.15, 443.62, (425,62,640,104)),
]
